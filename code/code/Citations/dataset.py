import json
import nltk
from nltk.corpus import stopwords

# template = ("The following are conversations between a patient and a doctor. You will answer as a helpful doctor for proposing the solution for a patient's questions. "
#         "Write a response based on the facts.\n\n"
#         "### Description:\n{description}\n\n### {utterances}\n\n### <DOCTOR>:\n")

# entity_template = ("The following are conversations between a patient and a doctor. " 
#         "The keywords of the conversation are {keywords}. " 
#         "Given the keywords you will answer as a helpful doctor for proposing the solution for a patient's questions. "
#         "Write a response based on the facts.\n\n"
#         "### Description:\n{description}\n\n### {utterances}\n\n### <DOCTOR>:\n")

# no_desc_template = ("The following are conversations between a patient and a doctor. You will answer as a helpful doctor for proposing the solution for a patient's questions. "
#         "Write a response based on the facts.\n\n"
#         "### {utterances}\n\n### <DOCTOR>:\n")

# no_desc_entity_template = ("The following are conversations between a patient and a doctor. " 
#         "The keywords of the conversation are {keywords}. " 
#         "Given the keywords you will answer as a helpful doctor for proposing the solution for a patient's questions. "
#         "Write a response based on the facts.\n\n"
#         "### {utterances}\n\n### <DOCTOR>:\n")


template = ("[INST]The following are conversations between a patient and a doctor. You will answer as a helpful doctor for proposing the solution for a patient's questions. "
        "Write a response based on the facts.\n\n"
        "### Description:\n{description}\n\n### {utterances}\n\n### <DOCTOR>:\n[/INST]")

entity_template = ("[INST]The following are conversations between a patient and a doctor. " 
        "The keywords of the conversation are {keywords}. " 
        "Given the keywords you will answer as a helpful doctor for proposing the solution for a patient's questions. "
        "Write a response based on the facts.\n\n"
        "### Description:\n{description}\n\n### {utterances}\n\n### <DOCTOR>:\n[/INST]")

no_desc_template = ("[INST]The following are conversations between a patient and a doctor. You will answer as a helpful doctor for proposing the solution for a patient's questions. "
        "Write a response based on the facts.\n\n"
        "### {utterances}\n\n### <DOCTOR>:\n[/INST]")

no_desc_entity_template = ("[INST]The following are conversations between a patient and a doctor. " 
        "The keywords of the conversation are {keywords}. " 
        "Given the keywords you will answer as a helpful doctor for proposing the solution for a patient's questions. "
        "Write a response based on the facts.\n\n"
        "### {utterances}\n\n### <DOCTOR>:\n[/INST]")



# Download the stopwords from NLTK
nltk.download('stopwords')

# Get English stopwords
stopwords_list = set(stopwords.words('english'))
stopwords_list = set(stopwords.words('english'))
custom_unwanted_tokens = {"]", "=", "[", "(", ")", "'", "/", "s","-"}  # Add more if needed
unwanted_tokens = stopwords_list.union(custom_unwanted_tokens)


def entity_in_context(sentence, nlp_pipelines):
    unique_entities = {}  # Now a dictionary to maintain original case

    for entity_type, nlp in nlp_pipelines.items():
        ner_results = nlp(sentence)
        current_full_word = ''
        current_full_word_original = ''  # Track original casing

        for entity in ner_results:
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
    filtered_entities = [original for lower, original in unique_entities.items() if lower not in unwanted_tokens]
    return filtered_entities


def process_query(x, per_turn=True, eos_token="<eos>", ner_pipelines=None):
    queries = []

    utterances  = ''
    if 'description' in x.keys():
        template_cls = template if ner_pipelines is None else entity_template
    else:
        template_cls = no_desc_template if ner_pipelines is None else no_desc_entity_template

    for i, y in enumerate(x['utterances']):
        if i % 2 == 0:
            utterances += f'<PATIENT>:\n{y.replace("patient: ", "")}{eos_token}\n\n'
        else:
            y = y.replace("doctor: ", "")
            x['utterances'] = utterances
            if ner_pipelines is not None:
                entities = entity_in_context(utterances, ner_pipelines)
                x['keywords'] = ', '.join(entities)
            queries.append({ 
                'text': template_cls.format_map(x),
                'target': y
                })                
            utterances += f'<DOCTOR>: \n{y}{eos_token}\n\n'
    if per_turn:
        return queries
    return [queries[-1]]


def get_dataset(data_path, per_turn, eos_token, ner_pipelines=None):
    # data = load_dataset('json', data_files=data_path)

    f = open(data_path)
    data = json.load(f)
        
    queries = []
    for x in data:
        queries.extend(process_query(x,per_turn=per_turn, eos_token=eos_token, ner_pipelines=ner_pipelines))
    return queries

