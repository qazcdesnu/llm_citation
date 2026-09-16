import re
import math
import pandas as pd
from tqdm import tqdm

from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
from nltk.translate.bleu_score import sentence_bleu

import torch
from torch import cuda, bfloat16
from torch.nn.functional import softmax

import transformers
from transformers import BertTokenizer, BertModel, AutoTokenizer, LlamaForCausalLM, pipeline
from sentence_transformers import SentenceTransformer

import evaluate

from utils import parse_citation_args
from models import get_ner_model


exact_match = evaluate.load("exact_match")
stopwords_list = set(stopwords.words('english'))
ps = PorterStemmer()
custom_unwanted_tokens = {"]", "=", "[", "(", ")", "'", "/", "s","-",","}  # Add more if needed
unwanted_tokens = stopwords_list.union(custom_unwanted_tokens)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

model_identifiers = {
    'disease': "alvaroalon2/biobert_diseases_ner",
    'genetic': "alvaroalon2/biobert_genetic_ner",
    'chemical': "alvaroalon2/biobert_chemical_ner"
}
ner_pipelines = {}
for entity_type, identifier in model_identifiers.items():
    model, tokenizer = get_ner_model(identifier)
    ner_pipelines[entity_type] = pipeline("ner", model=model, tokenizer=tokenizer, device=device)


def causal_attn_calc(S, D, H=768):
    QK = torch.matmul(S, D.T)
    QK = torch.softmax(QK / math.sqrt(H), dim=-1)
    S_prime = torch.matmul(QK, D)

    S_abs = torch.abs(S_prime)
    S_mean = torch.mean(S_abs)

    S_prime = torch.where(S_abs < S_mean, 0, S_prime)

    S_prime_D = torch.matmul(S_prime, D.T)
    S_prime_D = torch.softmax(S_prime_D, dim=-1)    

    return S_prime_D

def jaccard(set1, set2):
    # intersection of two sets
    intersection = len(set1.intersection(set2))
    # Unions of two sets
    union = len(set1.union(set2))     
    return intersection / union if union != 0 else 0

def keyword_jaccard(sentences, documents):

    result = torch.zeros((len(sentences), len(documents)))

    key_sent = entity_in_contexts(sentences, ner_pipelines)
    key_sent = [stem_entities(x) for x in key_sent]

    key_doc = entity_in_contexts(documents, ner_pipelines)
    key_doc = [stem_entities(x) for x in key_doc]
    # breakpoint()

    for s_idx, s in enumerate(sentences):
        for d_idx, d in enumerate(documents):
            result[s_idx][d_idx] = jaccard(key_sent[s_idx], key_doc[d_idx])
    return result
            

def causal_jaccard(sentences, documents):

    result = torch.zeros((len(sentences), len(documents)))

    for s_idx, s in enumerate(sentences):
        for d_idx, d in enumerate(documents):
            cur_s = set([ps.stem(x) for x in s.lower().split(' ') if x not in stopwords_list])
            cur_d = set([ps.stem(x) for x in d.lower().split(' ') if x not in stopwords_list])
            result[s_idx][d_idx] = jaccard(cur_s, cur_d)

    return result

def vanilla_attn_calc(S, D):
    S_D = torch.matmul(S, D.T)
    return S_D

def stem_entities(entities):
    """Apply stemming to each entity in the set of entities."""
    stemmed_entities = set()
    for entity in entities:
        stemmed_entity = ps.stem(entity)
        stemmed_entities.add(stemmed_entity)
    return stemmed_entities

def entity_in_contexts(sentences, nlp_pipelines):
    list_of_unique_entities = [ list() for _ in range(len(sentences)) ]
    print('Running entitiy in contexts')
    def async_pipe(nlp, sentences):
        # sentences = ListDataset(sentences)
        # sentences = Dataset.from_list(sentences)
        # breakpoint()
        batch_size = max(len(sentences), 512)
        for x in tqdm(nlp(sentences), total=len(sentences)):
            yield x
    for i, (entity_type, nlp) in enumerate(nlp_pipelines.items()):
        # ner_results = nlp(sentences, batch_size=256)
        # breakpoint()
        ner_results = async_pipe(nlp, sentences)

        for ner_i, ner_result in enumerate(ner_results):
            current_full_word = ''
            current_full_word_original = ''  # Track original casing
            unique_entities = {}  # Now a dictionary to maintain original case

            for entity in ner_result:
                entity_type = entity['entity']

                if entity_type == '0':
                    if current_full_word:
                        # Normalize and add both lower and original case
                        unique_entities[current_full_word.lower()] = current_full_word_original
                        current_full_word = ''
                        current_full_word_original = ''
                    continue

                word = entity['word']
                if word.startswith("##"):
                    current_full_word += word[2:]
                    current_full_word_original += word[2:]  # Append to original
                else:
                    if current_full_word:
                        unique_entities[current_full_word.lower()] = current_full_word_original
                    current_full_word = word.lower()  # Normalize for comparison
                    current_full_word_original = word  # Keep original

            if current_full_word:
                unique_entities[current_full_word.lower()] = current_full_word_original

        # Filter out unwanted tokens including stopwords and specified special characters
            list_of_unique_entities[ner_i].extend( [original for lower, original in unique_entities.items() if lower not in unwanted_tokens] )
    return list_of_unique_entities

def get_text(per_sentence, documents, score_matrix, threshold=0):

    txt = ''
    used_docs = list()
    
    argmax_score_matrix = torch.argmax(score_matrix, dim=-1)

    for i in range(len(per_sentence)):
        # current_sentence = per_sentence[i]
        # S_prime_D_document = documents[argmax_score_matrix[i]]

        txt += f'{per_sentence[i]}.'

        if score_matrix[i][argmax_score_matrix[i]] > threshold:
            metadata = documents[argmax_score_matrix[i]].metadata
            page_content = documents[argmax_score_matrix[i]].page_content
            metadata['page_content'] = page_content
            if 'source' in metadata:
                txt += f'\n(Medline: {metadata["title"]})'
            else:
                txt += f'\n({metadata["first_author"]}, {metadata["year"]})'
            if metadata not in used_docs:
                used_docs.append(metadata)
            txt += '\n'
    txt += '\n\n'

    for x in used_docs:
        if 'source' in x:
            txt += f'\nMedline {x["title"]} url: {x["source"]}'
        else:
            txt += f'\n({x["first_author"]}, {x["year"]}) {x["title"]} url: doi.org/{x["doi"]}'
            # txt += f'\n{x["first_author"]} {x["title"]} url: doi.org/{x["doi"]}'
        txt += f'\n{x["page_content"]}\n'
    # breakpoint()
    return txt



def main():
    args = parse_citation_args()

    df = pd.read_pickle(args.pkl_file)
    
    if 'bert' in args.encoder:
        tokenizer = BertTokenizer.from_pretrained(args.encoder)
        model = BertModel.from_pretrained(args.encoder)
        H = model.config.hidden_size
        def vectorize(text):
            inputs = tokenizer(text, return_tensors='pt', max_length=512, truncation=True)
            outputs = model(**inputs)
            return outputs.last_hidden_state.mean(dim=1) 
    elif 'gtr' in args.encoder:
        model = SentenceTransformer('sentence-transformers/gtr-t5-xxl')
        vectorize = lambda x: model.encode(x)

    output_df = pd.DataFrame(columns = list(df.columns).extend(["causal_output", "default_output"]))

    for i, row in tqdm(df.iterrows()):
        output = row['output']
        documents = row['documents']['source_documents']

        cur_dict = row.to_dict()

        per_sentence = [x.strip() for x in re.split('[^0-9]["."][^0-9]', output) if x.strip() != '']
        document_contents = [x.page_content for x in row['documents']['source_documents'] ]
        
        if len(per_sentence) == 0:
            per_sentence = ['']

        sentece_vector = torch.stack([ vectorize(x) for x in per_sentence]).view(-1,H)
        S_N = sentece_vector.shape[0]
        document_vector = torch.stack([ vectorize(x) for x in document_contents]).view(-1, H)
        D_N = document_vector.shape[0]

        temperature = 0.7

        S_D = vanilla_attn_calc(sentece_vector, document_vector)
        S_D = torch.softmax(S_D / temperature, dim=-1)

        S_prime_D = causal_attn_calc(sentece_vector, document_vector, H)
        S_prime_D = torch.softmax(S_prime_D / temperature, dim=-1)


        kw_jacc_mat = keyword_jaccard(per_sentence, document_contents)
        kw_jacc_mat = torch.softmax(kw_jacc_mat / 0.05, dim=-1)

        jaccard_mat = causal_jaccard(per_sentence, document_contents)
        jaccard_mat = torch.softmax(jaccard_mat / temperature, dim=-1)
        # breakpoint()


        cur_dict['vanilla_output'] = get_text(per_sentence, documents, S_D)
        cur_dict['jaccard_output'] = get_text(per_sentence, documents, jaccard_mat)
        cur_dict['kw_jaccard_output'] = get_text(per_sentence,documents, kw_jacc_mat, threshold=0.2)



        output_df = pd.concat([output_df, pd.DataFrame.from_records([cur_dict])])





    save_path = args.pkl_file.split('.')
    save_path = f'{save_path[0]}-kwj-citation.pkl'
    output_df.to_pickle(save_path)    

if __name__ == '__main__':
    main()
