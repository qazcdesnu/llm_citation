import urllib.request
from tqdm import tqdm
import os

for i in tqdm(range(1167)):
    url_path  = f'https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/pubmed23n{i:04d}.xml.gz'
    urllib.request.urlretrieve(url_path, os.path.join('pubmed', f'pubmed23n{i:04d}.xml.gz'))
