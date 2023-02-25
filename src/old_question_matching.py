import pandas as pd
import os
import pickle
import Levenshtein
import spacy
from collections import defaultdict
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from collections import Counter
from strsimpy.ngram import NGram
from statistics import mean
from strsimpy.longest_common_subsequence import LongestCommonSubsequence
from strsimpy import SIFT4
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from text2vec import SentenceModel, cos_sim, semantic_search, BM25
from src.check_functions import check_all_FAQ, one_to_all
import statistics

#initialize models
nlp = spacy.load("zh_core_web_lg")
model = SentenceModel('../text2vec/')

faq_path = '../midea/0531/菜谱评论数据/已标注/' # path to faq files
qDB_path = '../food_data/scraping_xiachufang/collected/' # path to scraped comments from xiachufang

with open('data/translate_recipe_name.pickle', 'rb') as handle:
    translate_recipe_name = pickle.load(handle)

# aux function to count overlap words between two strings (without stopwords)
stop_words = nlp.Defaults.stop_words
def count_overlap(s1, s2):
    count = 0
    for tok in nlp(s1):
        if tok.text not in stop_words:
            if tok.text in s2:
                s2 = s2.replace(tok.text, '')
                count += 1
    return count

# aux function to get the mean of ngram count
def get_ngram_mean(max_ngram, s1, s2):
    aux = []
    for n in range(1, max_ngram):
        ngram = NGram(n)
        aux.append(ngram.distance(s1, s2))
    return (mean(aux))

#
def check_overlap(q, poss_ans):
    q_dict = check_all_FAQ(q)
    flag = True
    if len(q_dict) > 0:
        for k,v in q_dict.items():
            if k == 'ingredients':
                for ing in v:
                    if ing in poss_ans:
                        poss_ans = poss_ans.replace(ing, '')
                    elif ing in one_to_all.keys() and any(ele in poss_ans for ele in one_to_all[ing]):
                        poss_ans = poss_ans.replace(ing, '') ## check
                    else:
                        flag = False
                        break
            else:
                if v in poss_ans:
                    poss_ans = poss_ans.replace(v, '')
                else:
                    flag = False
                    break
    else:
        flag = False
    return flag

# aux function to find the most frequent (repetitive) string in a list
def find_most_frequent(List):
    occurence_count = Counter(List)
    return occurence_count.most_common(1)[0][0]

# find files related to recipe name
def find_files(recipe):
    file = recipe + '.xlsx'
    faq = os.listdir(faq_path)
    qDB = os.listdir(qDB_path)
    # FAQ
    if file in faq:
        r1 = pd.read_excel(faq_path+'{}'.format(file), header=None)
        qa_dict = {}
        for index, row in r1.to_dict('index').items():
            ans = 'answer{}'.format(index)
            for k,v in row.items():
                if not isinstance(v, float):
                    qa_dict[v] = ans
    else:
        qa_dict = {}
    # Recipe comments
    if file in qDB:
        dbq = pd.read_excel(qDB_path+'{}'.format(file))
        db_dict = {}
        for i, row in dbq.iterrows():
            db_dict[row['问题']] = row['回答'].strip() if not isinstance(row['回答'], float) else 'unk'
    elif recipe in translate_recipe_name.keys():
        oname = translate_recipe_name[recipe]
        file = oname + '.xlsx'
        db_dict = {}
        try:
            dbq = pd.read_excel(qDB_path+'{}'.format(file))
            for i, row in dbq.iterrows():
                db_dict[row['问题']] = row['回答'].strip() if not isinstance(row['回答'], float) else 'unk'
        except:
            for file in qDB:
                if recipe in file:
                    dbq = pd.read_excel(qDB_path+'{}'.format(file))
                    for i, row in dbq.iterrows():
                        db_dict[row['问题']] = row['回答'].strip() if not isinstance(row['回答'], float) else 'unk'
    else:
        possible_recipes = []
        for file in qDB:
            if recipe in file:
                possible_recipes.append(file)
        # select the first one, but actually can give user options to choose from
        dbq = pd.read_excel(qDB_path+'{}'.format(possible_recipes[0]))
        db_dict = {}
        for i, row in dbq.iterrows():
            db_dict[row['问题']] = row['回答'].strip() if not isinstance(row['回答'], float) else 'unk'

    question_dict = {**qa_dict, **db_dict}
    return qa_dict

lcs = LongestCommonSubsequence()
s = SIFT4()

# ensemble method for string similarity
def get_most_similar(user_q, question_matching):
    if len(question_matching) > 0:
        match1, match2, match3, match4, match5, match6, match7 = '', '', '', '', '', '', ''
        # ------------- overlap --------------
        max_overlap = 0
        for orig_question, matched_questions in question_matching.items():
            for matched_question in matched_questions:
                c = count_overlap(orig_question, matched_question[0])
                if c > max_overlap:
                    max_overlap = c
                    match1 = matched_question[0]
       # -------------- sift4 -----------------
        distance = 2**8
        for orig_question, matched_questions in question_matching.items():
            for matched_question in matched_questions:
                c = s.distance(orig_question, matched_question[0])
                if c < distance:
                    distance = c
                    match2 = matched_question[0]
        # -------------- ngram ----------------
        ngram_mean_value = 0
        max_len_ngram = 5
        for orig_question, matched_questions in question_matching.items():
            for matched_question in matched_questions:
                c = get_ngram_mean(max_len_ngram, orig_question, matched_question[0])
                if c > ngram_mean_value:
                    ngram_mean_value = c
                    match3 = matched_question[0]
        # ------------ levenshtein -------------
        min_distance = 2**8
        for orig_question, matched_questions in question_matching.items():
            for matched_question in matched_questions:
                c = Levenshtein.distance(orig_question, matched_question[0])
                if c < min_distance:
                    min_distance = c
                    match4 = matched_question[0]
        # ------------ subseq -----------------
        longest_subseq = 0
        for orig_question, matched_questions in question_matching.items():
            for matched_question in matched_questions:
                c = lcs.distance(orig_question, matched_question[0])
                if c > longest_subseq:
                    longest_subseq = c
                    match5 = matched_question[0]
        # ----------- rank n1 -----------------
        match6 = question_matching[user_q][0][0]

        # ---------- embedding ----------------
        for orig_question, matched_questions in question_matching.items():
            choices = [x[0] for x in matched_questions]
            embeddings1 = model.encode([orig_question])
            embeddings2 = model.encode(choices)
            cosine_scores = cos_sim(embeddings1, embeddings2)
            sim = 0
            for j in range(len(choices)):
                # if the cosine_scores are already ordered we can just return the first result (highest sim)
                if cosine_scores[0][j] > sim:
                    sim = cosine_scores[0][j]
                    match7 = choices[j]

        most_freq = find_most_frequent([match1, match2, match3, match4, match5, match6, match7])
        matched_dict = dict(question_matching[user_q])
        res = (user_q, most_freq, matched_dict[most_freq])
    else:
        res = '抱歉，小助手没找到相关的答案'
    return res

# given a question find the most similar in related file and return triple (user_question, matched_question, answer)
###### ----------->  DEPRECATED  <-------------- ##########
def match_faq(rec, user_q):
    #rec = check_recipies(user_q)
    questions_dict = find_files(rec)
    choices = questions_dict.keys()
    question_matching = defaultdict(list)

    # first filter, similarity >= 50
    matched_tuples = process.extract(user_q, choices, scorer=fuzz.ratio)
    for match in matched_tuples:
        if match[1] >= 50:
            question_matching[user_q].append((match[0], questions_dict[match[0]]))

    # second filter, ensemble model
    most_sim_tuple = get_most_similar(user_q, question_matching)
    return most_sim_tuple

'''
Matching pipeline for FAQ
input: user's question [type: string]
output: (original_question, matched_question, matched_question_answer) [type: tuple]
parameters: first filter threshold (0.9), second filter std_deviation (BM25: 0.5), overlap value (c) 
'''
import statistics
from text2vec import SentenceModel, cos_sim, semantic_search, BM25

# model = SentenceModel('../../text2vec/')

'''
Matching pipeline for FAQ
input: user's question [type: string]
output: (original_question, matched_question, matched_question_answer) [type: tuple]
'''


def match_faq2(rec, user_q):
    # find related files
    #rec = check_recipies(user_q)
    user_q = user_q.replace(rec, '')
    questions_dict = find_files(rec)
    questions_dict['NOT FOUND'] = '找不到相关的答案，要不换个问题试试吧'

    # Query
    queries = [user_q]
    # print(rec+user_q)

    # Corpus with example sentences
    corpus = list(questions_dict.keys())
    # corpus = [v['unmasked'] for k, v in masked_dict.items()]
    corpus_embeddings = model.encode(corpus)

    # Find the closest 5 sentences of the corpus for each query sentence based on cosine similarity
    top_k = min(5, len(corpus))
    match = None


    ########  use semantic_search to perform cosine similarty + topk
    for query in queries:
        query_embedding = model.encode(query)
        hits = semantic_search(query_embedding, corpus_embeddings, top_k=top_k)
        hits = hits[0]  # Get the hits for the first query
        aux_list = []
        for hit in hits:
            # print(corpus[hit['corpus_id']], hit['score'])
            if hit['score'] >= 0.9:
                #print(1)
                # print(corpus[hit['corpus_id']], "(Score: {:.4f})".format(hit['score']))
                #match = corpus[hit['corpus_id']]
                # check for EXACT overlap in both strings
                if check_overlap(user_q, corpus[hit['corpus_id']]):
                    match = corpus[hit['corpus_id']]
                    break

    # print('SPACY: ', get_most_sim_question1(user_q, aux_list))

    if match == None:
        ######## use bm25 to rank search score
        search_sim = BM25(corpus=corpus)
        aux_scores, aux_ans = [], []
        for query in queries:
            # q_dict = check_all_FAQ(query)
            possible_match_flag = False
            possible_match = None
            for i in search_sim.get_scores(query, top_k=top_k):
                # print(i[0], "(Score: {:.4f})".format(i[1]))
                aux_scores.append(i[1])
                aux_ans.append(i[0])
                poss_ans = i[0]
                # a_dict = check_all_FAQ(poss_ans)
                '''
                c = 0
                if not possible_match_flag and len(q_dict) > 0:
                    for k,v in q_dict.items():
                        if k == 'ingredients':
                            for ing in v:
                                if ing in poss_ans:
                                    poss_ans = poss_ans.replace(ing, '')
                                    c += 1
                        else:
                            if v in poss_ans:
                                poss_ans = poss_ans.replace(v, '')
                                c += 1

                    if c >= len(q_dict.values()):
                        possible_match = i[0]
                        possible_match_flag = True
                '''

            if len(aux_scores) > 2 and statistics.stdev(aux_scores) >= 0.5:
                for i in range(len(aux_ans)):
                    if check_overlap(user_q, aux_ans[i]):
                        match = (aux_ans[i])
                if match == None:
                    match = 'NOT FOUND'
                # print(2)
            # elif possible_match_flag:
            # print(3)
            #    match = possible_match
            else:
                match = 'NOT FOUND'
    return (user_q, match, questions_dict[match])
