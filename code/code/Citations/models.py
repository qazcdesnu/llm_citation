import torch
import transformers
from transformers import AutoModelForCausalLM, AutoModelForTokenClassification, AutoTokenizer

from langchain.llms import HuggingFacePipeline
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain



def get_gen_model(name):
    args = {
        'device_map': 'auto', 
        # 'torch_dtype':torch.bfloat16
    }
    return get_model(AutoModelForCausalLM,name, args), AutoTokenizer.from_pretrained(name)

def get_ner_model(name):
    args = {
        'torch_dtype':torch.bfloat16
    }
    return get_model(AutoModelForTokenClassification,name,args), AutoTokenizer.from_pretrained(name)

def get_model(cls, name, args):
    return cls.from_pretrained(
        name, 
        **args
    )

def get_llm_pipeline(model, tokenizer):
    tokenizer.pad_token = tokenizer.eos_token



    generate_text = transformers.pipeline(
        model=model, 
        tokenizer=tokenizer,
        return_full_text=True, 
        task='text-generation',
        temperature=0.1,  
        max_new_tokens=512,  
        repetition_penalty=1.1, 
        device_map="auto"
    )

    llm = HuggingFacePipeline(pipeline=generate_text)
    return llm

def get_retrieval_embedding(name):
    model_kwargs = {"device": "cuda"}
    embeddings = HuggingFaceEmbeddings(model_name=name, model_kwargs=model_kwargs,)
    return embeddings

def get_pipeline(vector_db, embeddings, llm, top_k):
    new_db = FAISS.load_local(vector_db, embeddings)
    vector_store = new_db.as_retriever(search_kwargs={"k": top_k})
    chain = ConversationalRetrievalChain.from_llm(llm, vector_store, return_source_documents=True)
    # breakpoint()
    return chain
