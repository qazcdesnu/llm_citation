from torch import cuda, bfloat16
import transformers
from langchain.document_loaders import WebBaseLoader, UnstructuredXMLLoader, DataFrameLoader
from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.text_splitter import HTMLHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain.llms import HuggingFacePipeline, OpenAI
from transformers import StoppingCriteria, StoppingCriteriaList
import torch
import os
import glob
import json 

import pickle
from tqdm import tqdm
import pandas as pd
import xml.etree.ElementTree as ET

from langchain.document_loaders.merge import MergedDataLoader
from  langchain.schema import Document


def save_docs_to_jsonl(array, file_path:str)->None:
    with open(file_path, 'w') as jsonl_file:
        for doc in array:
            jsonl_file.write(doc.json() + '\n')

def load_docs_from_jsonl(file_path):
    array = []
    with open(file_path, 'r') as jsonl_file:
        for line in jsonl_file:
            data = json.loads(line)
            obj = Document(**data)
            array.append(obj)
    return array
    


df_path = '/dataset/pubmed_df_year/*.pkl'
list_of_df_path = glob.glob(df_path)
df = pd.concat(map(pd.read_pickle,list_of_df_path), axis=0, ignore_index=True)

print('-'*80)
print(f'loaded {len(df)} dataframe')

df_loader = DataFrameLoader(df, page_content_column="abstract")

with open('medline_urls.json', 'r') as file:
    data = json.load(file)
web_links = data
web_loader = WebBaseLoader(web_links)


loader_all = MergedDataLoader(loaders=[df_loader, web_loader])


print('getting all docs')
docs_all = loader_all.load()


# save_docs_to_jsonl(docs_all,'data.jsonl')
# docs_all=load_docs_from_jsonl('data.jsonl')

def clean_document(doc):
    # Clean the page_content attribute
    cleaned_content = doc.page_content.replace('\n', ' ')
    cleaned_content = ' '.join(cleaned_content.split())

    doc.page_content = cleaned_content
    return doc

# Assuming all_splits is a list of Document objects
cleaned_docs = [clean_document(doc) for doc in docs_all]


text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
all_splits = text_splitter.split_documents(cleaned_docs)



model_name = "BAAI/bge-large-en-v1.5"
model_kwargs = {"device": "cuda"}

embeddings = HuggingFaceEmbeddings(
    model_name=model_name, 
    model_kwargs=model_kwargs, 
    # multi_process=True,
)



print('vectorizing')

db = FAISS.from_documents(all_splits, embeddings, distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)




db.save_local('pubmed_medline_year_all_bge-large')

