# GSDS 서버 Slurm GPU 작업 유의사항

출처: GSDS 서버 매뉴얼 <https://gsds.gitbook.io/gsds/> (매뉴얼 최종 수정 2024.05.07)
작성일: 2026-09-24. 매뉴얼 내용에 **실제 서버에서 `sinfo` / `scontrol`로 확인한 값**을 더했습니다(§1).
매뉴얼과 실제 서버가 다른 부분은 ⚠️로 표시했습니다.

---

## 0. 핵심 요약 (이것만은 지키기)

1. **로그인 노드에서는 프로그램을 실행하지 않는다.** 가벼운 문서 편집만 허용된다. 적발되면 관리자가 프로세스를 kill한다.
   `python`, `pip install` 대량 빌드, 데이터 전처리, 모델 다운로드도 모두 GPU 노드에서 한다.
2. **실제 실험은 `sbatch` / `srun`으로 한다.** `launch-shell`, `launch-jupyter`는 **디버깅용**이다(최대 4시간).
   자원을 잡아두고 놀리는 경우가 가장 흔한 위반 사례다.
3. **GPU는 1인당 최대 8장.** 대기열이 비어 있을 때만 더 써도 된다. (Advanced 문서 기준 상한은 4노드/16 GPU를 지양)
4. **필요한 만큼만 요청한다. GPU만이 아니라 CPU와 메모리도 해당한다.** CPU나 메모리를 과하게 잡으면 그 노드의 남는 GPU를 다른 사람이 못 쓴다.
5. **작업당 최대 12시간.** 더 긴 작업은 체크포인트를 저장하고 requeue나 dependency로 이어서 돌린다(§5).
6. **계정 공유는 절대 금지.** 적발되면 계정이 정지된다.
7. 규정에 맞지 않는 job은 **관리자가 cancel**하며 페널티가 있을 수 있다.

---

## 1. 클러스터 구성 (실측, 2026-09-24)

| 노드 | 역할 |
| --- | --- |
| 로그인 노드 (login1/2/3) | GPU 노드 접속용. **실행 금지** |
| GPU 노드 | Slurm으로 할당받아 모든 작업을 수행 |
| 스토리지 노드 | NFS로 모든 노드에 `/home`, `/shared`를 마운트 |

| Partition | 노드 | GPU | 노드당 CPU / 메모리 | 시간 제한 | 비고 |
| --- | --- | --- | --- | --- | --- |
| **`P2`** (기본값) | b[00-31], 32대 | RTX 3090 24GB × 4 (일부 노드 3장 또는 8장) | 128 코어 / ~410GB | **12:00:00** | 전체 GPU 131장 |
| `P3` | c[00-01], 2대 | RTX 4090 24GB × 4 | 128 코어 / ~410GB | 12:00:00 | |
| `causal1` | b02, b06 | RTX 3090 × 4 | 128 코어 / ~410GB | 무제한 | `lab03` 그룹 전용. P2와 같은 노드를 공유하므로 사용 전 랩 서버 담당자에게 확인할 것 |

⚠️ **매뉴얼의 partition 이름(`a`, `b`, `A`)은 예전 이름이다.** 현재는 `P2` / `P3`를 쓴다.
스크립트를 복사할 때 `--partition`을 반드시 고친다. 확인 명령은 `sinfo -s`이다.

⚠️ **GPU는 24GB가 최대다.** 서버에 48GB나 80GB 카드는 없다. 11B 이상 모델은 bf16, 양자화, 또는 다중 GPU로 나눠 올려야 한다.
(이 프로젝트의 AutoAIS T5-XXL 관련 내용은 `rebuttal/SERVER.md` §2 참고)

⚠️ **`DefMemPerNode = UNLIMITED`** 이다. 즉 `--mem`을 지정하지 않으면 노드 메모리를 과하게 잡을 수 있다.
**`--mem`과 `--cpus-per-task`는 항상 명시한다.**

기타 설정: `PreemptMode=REQUEUE`, `MaxArraySize=1001`, `MaxJobCount=10000`, `PriorityType=multifactor`

---

## 2. 접속

- **자기 랩에 배정된 로그인 노드로 접속한다** (부하 분산 목적).
  - login1 `147.47.200.192`: 이승근, 이재진, 이준석, 차상균, Wen Syan Li
  - login2 `147.47.200.188`: 김태섭, 오민환, 이상학, 이상원, 기타·미배정
  - login3 `147.47.200.22`: 김형신, **박현우(lab03)**, 이재윤, 조요한
  - ⚠️ 현재 계정(`jwkim`, 그룹 `lab03`)은 매뉴얼상 **login3** 배정이다. 작성 시점 세션은 login2에 접속되어 있었다.
- 포트: 학내망에서는 `22`, 외부에서는 **`22555`** (2024.01.17부터 22554에서 변경)
  ```bash
  ssh jwkim@147.47.200.22 -p 22555
  ```
- 처음 접속하면 `passwd`로 비밀번호를 변경한다.
- **VSCode Remote-SSH 사용 시**
  - 데이터가 많은 폴더를 Workspace로 열지 않는다. 대량 IO가 발생해 서버 전체가 느려진다.
  - 원격 Extension은 서버에 설치되어 백그라운드에서 돌 수 있다. 최소한만 설치하고 쓰지 않을 때는 비활성화한다.

---

## 3. 작업 실행 방법

### 3-1. `sbatch`: 실제 실험은 이 방식을 쓴다

```bash
#!/bin/bash
#SBATCH --job-name=llmcite-eval
#SBATCH --nodes=1
#SBATCH --gres=gpu:1                   # 필요한 GPU 수만 (특정 종류: gpu:rtx_3090:1)
#SBATCH --partition=P2                 # 매뉴얼의 a/b/A 아님!
#SBATCH --time=0-06:00:00              # 예상 시간 + 여유. 최대 12:00:00
#SBATCH --cpus-per-task=4              # 필요한 만큼만
#SBATCH --mem=32G                      # 반드시 명시 (DefMem 무제한)
#SBATCH --output=slurm_log/%x-%j.out   # %x=job name, %j=job id

source ${HOME}/.bashrc
source ${HOME}/anaconda3/bin/activate
conda activate llmcite

srun python run_experiments.py --eval --alce ~/ALCE
```

```bash
mkdir -p slurm_log         # --output 디렉터리가 없으면 로그가 남지 않는다
sbatch example.sh
squeue -u $USER            # 내 작업 확인
scancel <job_id>           # 중단
```

- `sbatch`는 자원이 없으면 큐에서 **기다렸다가** 실행한다. 여러 작업을 동시에 돌릴 때 적합하다.
- `--time`을 짧고 정확하게 잡을수록 스케줄링(backfill)에 유리하다.

### 3-2. `srun`: 단발성 명령

```bash
srun --gres=gpu:1 --cpus-per-task=4 --mem=16G --time=00:30:00 -p P2 nvidia-smi
```

### 3-3. `launch-shell` / `launch-jupyter`: 디버깅 전용

```bash
launch-shell [#GPUs] [timelimit(min)] [partition]
launch-jupyter [#GPUs] [conda env] [timelimit(min)] [partition]
```

- **최대 4시간.** 사용자가 쉬고 있어도 자원이 해제되지 않으므로 **다 쓰면 즉시 `exit`** 한다.
- 여러 작업을 돌려야 하면 이 방식이 아니라 `sbatch`를 쓴다.
- Jupyter URL의 노드 이름을 IP로 바꿔서 접속한다.
  a00–a11 → `147.47.200.192`, b00–b15 → `147.47.200.188`, b16–b31 → `147.47.200.22`
- ⚠️ 작성 시점에 `launch-jupyter`는 PATH에서 찾을 수 없었다(`launch-shell`만 `/usr/bin`에 있음).

---

## 4. 자원 요청 체크리스트

- [ ] `--partition=P2` (또는 `P3`)로 설정했는가?
- [ ] GPU 수가 코드가 실제로 쓰는 수와 같은가? (단일 GPU 코드에 `gpu:4`를 요청하지 않는다)
- [ ] `--mem`, `--cpus-per-task`를 명시했는가? DataLoader worker 수에 맞춘다.
- [ ] `--time` ≤ 12시간이고, 넘을 수 있다면 체크포인트와 재개 로직이 있는가?
- [ ] 동시에 쓰는 GPU 합계가 **8장 이하**인가? `squeue -u $USER`로 확인한다.
- [ ] 출력, 체크포인트, 모델 캐시가 홈 quota(100GB)를 넘지 않는가? (§6)

---

## 5. 12시간이 넘는 작업 (Slurm Advanced)

두 방법 모두 **`sbatch`에서만** 쓸 수 있고, 프로그램을 **처음부터 새로 실행**한다.
따라서 **체크포인트 저장과 재개 로직이 필수다.**

### 5-1. Requeue: 언제 끝날지 모르는 작업

```bash
#SBATCH --time=12:00:00
#SBATCH --signal=B:SIGUSR1@30          # 종료 30초 전에 SIGUSR1 발생
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append             # requeue돼도 같은 job_id라 로그를 이어서 쓴다

max_restarts=2
restarts=$(scontrol show job ${SLURM_JOB_ID} | grep -o 'Restarts=[0-9]*' | cut -d= -f2)

function resubmit() {
    if [[ $restarts -lt $max_restarts ]]; then
        scontrol requeue ${SLURM_JOB_ID}; exit 0
    else
        echo "Maximum restarts reached"; exit 1
    fi
}
trap 'resubmit' SIGUSR1

python train.py --resume &    # 반드시 백그라운드(&) + wait (그래야 trap이 동작)
wait
exit 0
```

> 매뉴얼 원문에는 `grep -o 'Restarts=[0-9]*****'`처럼 `*`가 여러 개 붙어 있는데, 이는 오타로 보인다. `[0-9]*`로 쓴다.

### 5-2. Dependency: 순차 실행 또는 동시 실행 수 제한

```bash
jid=$(sbatch --parsable step1.sh)
sbatch --dependency=afterok:${jid} step2.sh      # step1이 성공하면 실행
# afternotok:<id>  실패 시 실행 / afterany:<id>  종료 여부와 무관하게 실행
```

- dependency 자체는 서버에 부하를 주지 않는다. 그러나 **큐에 작업을 10,000개 이상 올리면 slurm이 멈춘다** (`MaxJobCount=10000`).
  대량 sweep은 job array(`--array=0-99%8`처럼 `%`로 동시 실행 수 제한, 최대 크기 1001)나 한 job 안의 루프로 묶는다.

---

## 6. 스토리지

- **개인 홈 quota는 100GB** (`/home/s3/jwkim`).
- **랩 공용 디렉토리** (10TB/랩): 박현우 교수님 랩은 **`/shared/s3/lab03`** (권한 `drwxrwx--- root:lab03`)
  - 큰 데이터셋, 모델 체크포인트, HF 캐시는 여기에 둔다. 홈이 부족할 때는 공용 디렉토리 안에 개인 폴더를 만든다.
  - 랩원과 함께 쓰는 폴더는 그룹 쓰기 권한을 준다. 예: `chmod -R 770 dir`
  - 홈에서 경로를 짧게 쓰려면 심볼릭 링크를 만든다. 예: `ln -s /shared/s3/lab03/jwkim ~/shared`
- LLM 작업 시 기본 캐시 경로가 홈이라 quota가 금방 찬다. 공용 디렉토리로 옮긴다:
  ```bash
  export HF_HOME=/shared/s3/lab03/jwkim/hf_cache
  export TORCH_HOME=/shared/s3/lab03/jwkim/torch_cache
  export PIP_CACHE_DIR=/shared/s3/lab03/jwkim/pip_cache
  ```
- 모든 노드가 NFS로 같은 파일을 본다. **수많은 작은 파일을 동시에 읽고 쓰면 전체 서버가 느려진다.**
- 스토리지 증설은 공용 디렉토리에 여유가 있으면 승인되지 않는다.

---

## 7. 기타

- **tmux**: 로그인 노드에서 `tmux`를 쓰면 SSH가 끊겨도 `launch-shell` 세션이 유지된다. 단, 세션은 직접 종료하거나 서버가 리부트되기 전까지 남는다.
  **다 쓴 세션은 `tmux kill-session -t <name>`으로 반드시 종료한다.** `sbatch`로 제출한 작업은 tmux 없이도 계속 실행된다.
- **Anaconda**: 홈에 설치한다(`~/anaconda3`). 설치 용량이 커서 quota를 차지하므로 miniconda를 쓰거나 env를 `/shared`에 두는 것도 고려한다.
- **문의**
  - 일반 질문은 **랩 서버 담당자**에게 한다. 전체 관리자에게 개별 DM은 보내지 않는다.
  - 비밀번호 초기화, 스토리지 증설, 자원 할당 요청은 매뉴얼 양식에 맞춰 **gsds-hpc1@aces.snu.ac.kr** 로 메일을 보낸다.
    - `[비밀번호 초기화] {계정명}`: 성명, 계정명, 사유
    - `[스토리지 증설] {계정명} – {현재} – {증설 후}`: 성명, 계정명, 현재 용량, 증설 후 용량, 사유
    - `[서버 자원 할당] {계정명}`: 성명, 계정명, 사유, 기간, 공용 사용자 (논문 마감 등으로 일정 기간 자원이 필요할 때)

---

## 부록: 자주 쓰는 명령

```bash
sinfo -s                                   # partition별 노드 상태 (A/I/O/T)
sinfo -o "%P %N %G %c %m"                  # partition별 GPU·CPU·메모리
squeue -u $USER                            # 내 작업
squeue -p P2 -t PD                         # P2 대기열
scontrol show job <id>                     # 작업 상세 (할당 노드, 사유 등)
sacct -j <id> --format=JobID,Elapsed,MaxRSS,State   # 끝난 작업의 실제 사용량. 다음 --mem 산정에 사용
scancel <id> / scancel -u $USER
```
