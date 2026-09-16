from tqdm import tqdm
import pandas as pd

from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu

import torch
from transformers import pipeline
from datasets import Dataset

from utils import parse_args
from models import get_gen_model, get_ner_model, get_llm_pipeline, get_retrieval_embedding, get_pipeline
from dataset import get_dataset

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)

entity_markers = {
    'DISEASE': " [Disease]",
    'GENETIC': " [Genetic]",
    'CHEMICAL': " [Chemical]"
}

def group_subwords_and_mark(text, ner_results, entity_markers):
    grouped_entities = []
    current_entity = []
    last_entity_type = None

    for entity in ner_results:
        if entity['entity'].split('_')[0] not in ['0', 'B-0', 'I-0']:
            entity_type = entity['entity'].split('_')[-1]
            if entity['entity'].startswith('B-') or last_entity_type != entity_type:
                if current_entity:
                    grouped_entities.append((current_entity, last_entity_type))
                current_entity = [(entity['word'], entity['start'], entity['end'])]
                last_entity_type = entity_type
            else:
                current_entity.append((entity['word'], entity['start'], entity['end']))
    if current_entity:
        grouped_entities.append((current_entity, last_entity_type))

    return grouped_entities

def format_grouped_entities(text, grouped_entities, entity_markers):
    formatted_text = ""
    last_end = 0
    for entities, entity_type in grouped_entities:
        start = entities[0][1]  
        end = entities[-1][2]  
        word = text[start:end]  

        formatted_text += text[last_end:start]

        if entity_type in entity_markers:
            formatted_text += word + entity_markers[entity_type] + " "
        last_end = end

    formatted_text += text[last_end:]
    return formatted_text

def ner_query(ner_models, query,args=None):
    formatted_text = ''
    all_ner_results = []
    for entity_type, model_data in ner_models.items():
        nlp = pipeline("ner", model=model_data['model'], tokenizer=model_data['tokenizer'], device=device)
        ner_results = nlp(query)
        for result in ner_results:
            result['entity'] = f"{result['entity']}_{entity_type.upper()}"
        all_ner_results.extend([result for result in ner_results if result['entity'].split('_')[0] not in ['0', 'B-0', 'I-0']])

    grouped_entities = group_subwords_and_mark(query, all_ner_results, entity_markers)
    formatted_text += format_grouped_entities(query, grouped_entities, entity_markers)
    return formatted_text

def llm_pipeline(llm_chain, query):
    result = llm_chain({"question": query, "chat_history": []})
    return result


def create_query(query, ner_models, args):  
    ner_result = ner_query(ner_models, query, args)
    return ner_result

def eval(dataset, llm_chain, args, ner_models=None):
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    df = pd.DataFrame(columns = ['B1', 'B2', 'R1', 'R2', 'RL'])

    for x in tqdm(dataset):
        query = x['text']
        target = x['target']
        if not args.use_entity_prompt and ner_models is not None:
            query = create_query(ner_models=ner_models, query=query, args=args)
        result = llm_pipeline(llm_chain, query)
        generation_output = result['answer']
        # breakpoint()
        score = dict()
        output = generation_output.replace(query, '')
        
        rouge = scorer.score(target, output)
        score['target'] = target
        score['input'] = query
        score['output'] = output
        score['R1'] = rouge['rouge1'].fmeasure
        score['R2'] = rouge['rouge2'].fmeasure
        score['RL'] = rouge['rougeL'].fmeasure
        score['documents'] = result
        score['B1'] = sentence_bleu([target], output, weights=(1, 0, 0, 0))
        score['B2'] = sentence_bleu([target], output, weights=(0.5, 0.5, 0, 0))
        df = pd.concat([df, pd.DataFrame.from_records([score])])    
    df.to_pickle(args.output_path)

def main():
    args = parse_args()

    ner_models = None
    ner_pipelines = None
    if args.ner_model is not None:
        model_identifiers = {
            'disease': "alvaroalon2/biobert_diseases_ner",
            'genetic': "alvaroalon2/biobert_genetic_ner",
            'chemical': "alvaroalon2/biobert_chemical_ner"
        }
        if args.use_entity_prompt:
            model_identifiers = {
                "genetic": "alvaroalon2/biobert_genetic_ner",
                "chemical": "alvaroalon2/biobert_chemical_ner",
                "etc": "samrawal/bert-base-uncased_clinical-ner"
            }
        ner_models = {}
        ner_pipelines = {}
        for entity_type, identifier in model_identifiers.items():
            model, tokenizer = get_ner_model(identifier)
            ner_models[entity_type] = {'tokenizer': tokenizer, 'model': model}
            ner_pipelines[entity_type] = pipeline("ner", model=model, tokenizer=tokenizer, device=device)

    gen_model, gen_tokenizer = get_gen_model(args.gen_model)
    gen_tokenizer.pad_token = gen_tokenizer.eos_token

    if args.use_tp:
        import tensor_parallel as tp
        gen_model = tp.tensor_parallel(gen_model)
    else:
        # gen_model = gen_model.to(device)
        pass

    llm_pipeline = get_llm_pipeline(model=gen_model, tokenizer=gen_tokenizer)
    retrieval_embedding = get_retrieval_embedding(args.retrieval_embedding)
    chain = get_pipeline(args.vector_db, retrieval_embedding, llm_pipeline, args.top_k)

    dataset = get_dataset(data_path=args.test_path, per_turn=args.per_turn, eos_token="", ner_pipelines=ner_pipelines)

    dataset = Dataset.from_list(dataset)
    eval(dataset, llm_chain=chain, args=args, ner_models=ner_models)


if __name__ == '__main__':
    main()