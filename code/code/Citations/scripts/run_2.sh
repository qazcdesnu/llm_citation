#!/bin/bash

export CUDA_VISIBLE_DEVICES=0
export HUGGING_FACE_HUB_TOKEN=""

MODEL="opt_7b"
# MODEL="llama2_chat"

DATASET="meddialog"

PER_TURN_BOOL=false

NER_BOOL=false
ENTITY_BOOL=false

case $MODEL in 
    "llama_7b") MODEL_NAME="huggyllama/llama-7b"; ;;
    "llama_13b") MODEL_NAME="huggyllama/llama-13b"; ;;
    "llama2_7b") MODEL_NAME="meta-llama/Llama-2-7b-hf"; ;;
    "llama2_13b") MODEL_NAME="meta-llama/Llama-2-13b-hf"; ;;
    "llama2_7b_chat") MODEL_NAME="meta-llama/Llama-2-7b-chat-hf"; ;;
    "llama2_13b_chat") MODEL_NAME="meta-llama/Llama-2-13b-chat-hf"; ;;
    "vicuna") MODEL_NAME="lmsys/vicuna-7b-v1.5"; ;;
    "mistral_7b") MODEL_NAME="mistralai/Mistral-7B-v0.1"; ;;
    "mistral_inst_7b") MODEL_NAME="mistralai/Mistral-7B-v0.1"; ;;
    "mistral_7b") MODEL_NAME="mistralai/Mistral-7B-Instruct-v0.1"; ;;
    "opt_7b") MODEL_NAME="facebook/opt-6.7b"; ;;
    "gpt_7b") MODEL_NAME="EleutherAI/gpt-j-6b"; ;;
esac


case $DATASET in
   "meddialog") DATAPATH="dataset/meddialog-test.json"; ;;
esac

OUTPUT_PATH="result/$MODEL-$DATASET"

if [[ $NER_BOOL == true ]]; then
    OUTPUT_PATH="$OUTPUT_PATH-ner"
    NER_MODEL="--ner_model use"
else
    OUTPUT_PATH="$OUTPUT_PATH-vanilla"
    NER_MODEL=""
fi

if [[ $ENTITY_BOOL == true ]]; then
    OUTPUT_PATH="$OUTPUT_PATH-entity"
    ENTITY_PROMPT="--use_entity_prompt"
else
    OUTPUT_PATH="$OUTPUT_PATH-no_entity"
    ENTITY_PROMPT=""
fi

OUTPUT_PATH="${OUTPUT_PATH}.pkl"

python main.py \
    --gen_model  $MODEL_NAME \
    $NER_MODEL \
    --test_path $DATAPATH \
    --retrieval_embedding BAAI/bge-large-en-v1.5 \
    $ENTITY_PROMPT \
    --vector_db pubmed_medline_year_partial_bge-large \
    --top_k 6 \
    --output_path $OUTPUT_PATH


python citation.py \
    --pkl_file $OUTPUT_PATH \
    --encoder bert-base-uncased \
