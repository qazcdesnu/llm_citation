import sys
import argparse

def parse_args():
    print(sys.argv)
    parser = argparse.ArgumentParser()

    parser.add_argument('--test_path', default='')

    parser.add_argument('--ner_model', default=None)
    parser.add_argument('--gen_model', default='')

    parser.add_argument('--use_tp', default=False, action='store_true')
    parser.add_argument('--use_entity_prompt', default=False, action='store_true')

    parser.add_argument('--retrieval_embedding', default='BAAI/bge-large-en-v1.5')
    parser.add_argument('--vector_db', default='')
    parser.add_argument('--per_turn', default=False, action='store_true')
    parser.add_argument('--top_k', default=15, type=int)
    parser.add_argument('--output_path', default="result")
    return parser.parse_args()

def parse_citation_args():
    print(sys.argv)
    parser = argparse.ArgumentParser()

    parser.add_argument('--pkl_file', default='')

    parser.add_argument('--encoder', default='')

    return parser.parse_args()



