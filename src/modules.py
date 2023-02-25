import functools as ft
import pandas as pd
import os
import kglab
import pickle
from src.aux_functions import extract_steps_properties
from src.aux_functions import build_steps_dict
from src.aux_functions import decode_steps
from src.aux_functions import build_ing_composition_dict
from src.aux_functions import post_process_query
from src.aux_functions import q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13, q14
from src.check_functions import check_all
from src.check_functions import ingredients
from src.check_functions import check_ingredients
from src.check_functions import check_recipies
from src.check_functions import check_x_replaceble
from src.check_functions import check_kw_in_recipe
from src.check_functions import action_words
from src.check_functions import ing_composition_kw, one_to_all, all_to_one
from src.construct_graph import construct_kg
from src.construct_graph import popularity_dict
from src.question_matching import match_faq, match_faq2
from data.templates.constraint_queries import constraint_queries
from data.templates.crowd_constraint_queries import crowd_constraint_queries
from data.templates.constraint_queries_segments import constraint_queries_segments
from data.templates.ingredient_queries import ingredient_queries
from data.templates.property_queries import property_queries
from data.templates.relationship_query import relationship_query
from data.templates.replacemet_queries import replacemet_queries

#kg_path = 'data/kg.ttl'
kg_path = 'notebooks/kg.ttl'

# load ingredient constraints
with open('data/crowd_constraint.pickle', 'rb') as handle:
    ing_constraints = pickle.load(handle)

'''
CLASSIFICATION & ARGUMENT EXTRACTION MODULE
'''
def classify_question(q, user):
    q_args = check_all(q)
    res_dict = dict()
    # '咖喱土豆肉丸的主食'
    if 'recipe' in q_args.keys() and 'properties' in q_args.keys() and '怎么办' not in q and '现成' not in q and 'cooking_method' not in q_args.keys():
        # make sure 怎么办 is not in the question because these kind of sentences usually will go to the FAQ section
        # we also make sure there's not a cooking mathod for the same reason
        if '预热' not in q and '温度' not in q: # q_args['properties'] == '耗时' and 
            res_dict['question_type'] = 'recipe_property'
            res_dict['args'] = q_args
        else:
            res_dict['question_type'] = 'unknown'
    # the above condition may be too big, so make this new condition to catch some possible errors
    elif 'recipe' in q_args.keys() and 'properties' in q_args.keys() and 'cooking_method' in q_args.keys() and q_args['properties'] == '工具' :
        res_dict['question_type'] = 'recipe_property'
        res_dict['args'] = dict((k, q_args[k]) for k in ['recipe', 'properties'] if k in q_args)
    # '鸡翅跟腌料的比例'
    #elif 'recipe' in q_args.keys() and 'ingredients' in q_args.keys() and len(q_args['ingredients']) > 1 and '比例' in q:
    #    res_dict['question_type'] = 'relationship_query'
    #    res_dict['args'] = q_args
    # '咖喱土豆肉丸要多少肉' or maybe it's talking about ingredient replacement
    elif 'recipe' in q_args.keys() and 'ingredients' in q_args.keys():
        #if check_x_replaceble(q) != {}:
        #    res_dict['question_type'] = 'replacement_query'
        #    res_dict['args'] = check_x_replaceble(q)
        if ('多少' in q or '几' in q) or ('要放' in q or '需要' in q) and 'cooking_method' not in q_args.keys() and any(ele in q for ele in action_words) == False and '为什么' not in q: # !!!!!!!!!!!!
            res_dict['question_type'] = 'relationship_query'
            res_dict['args'] = q_args
        # this is the case where a recipe name could be an ingredient too ！！！！！！
        elif q_args['recipe'] in ingredients: #check_ingredients(q_args['recipe']) != []:
            res_dict['question_type'] = 'constraint_query'
            res_dict['args'] = {'ingredients': q_args['ingredients']}
            res_dict['args']['ingredients'].append(q_args['recipe']) #append(check_ingredients(q_args['recipe'])[0])
        else:
            res_dict['question_type'] = 'unknown'
    # '烤箱能做面包吗'
    elif 'tool' in q_args.keys() and 'recipe' in q_args.keys() and 'renqun' not in q_args.keys(): 
        res_dict['question_type'] = 'constraint_query'
        res_dict['aux_info'] = q_args['recipe']
        del q_args['recipe']
        res_dict['args'] = q_args
    # '咸香炒的小吃有哪些' or maybe it's talking about cooking tool replacement
    elif ('tool' in q_args.keys() or 'flavor' in q_args.keys() or 'cooking_method' in q_args.keys() or 'tags' in q_args.keys() or 'difficulty' in q_args.keys()) and 'recipe' not in q_args.keys() and 'renqun' not in q_args.keys():
        #if check_x_replaceble(q) != {}:
        #    res_dict['question_type'] = 'replacement_query'
        #    res_dict['args'] = check_x_replaceble(q)
        if ('哪' in q and '菜' in q) or '吃啥' in q or '吃什' in q or (('推荐' in q or '有' in q or '什么' in q) and '菜' in q): # !!!!!!!!!!!
            res_dict['question_type'] = 'constraint_query'
            res_dict['args'] = q_args
        else:
            res_dict['question_type'] = 'unknown'
    # '以土豆为主食的菜有哪些'
    elif 'ingredients' in q_args.keys() and 'ingredient_prop' not in q_args.keys() and 'renqun' not in q_args.keys() and \
    (('哪' in q and '菜' in q)  or '吃啥' in q or '吃什' in q or (('推荐' in q or '有' in q or '什么' in q) and '菜' in q)): # !!!!!!!!!!!::
        res_dict['question_type'] = 'constraint_query'
        res_dict['args'] = q_args
    # '番茄和什么菜好搭配'
    elif 'ingredients' in q_args.keys() and 'ingredient_prop' in q_args.keys():
        res_dict['question_type'] = 'ingredient_property'
        res_dict['args'] = q_args
        for kw in ing_composition_kw:
            if kw in q:
                res_dict['aux_info'] = kw
    # this is the case where a recipe name could be an ingredient too ！！！！！！
    elif 'recipe' in q_args.keys() and 'ingredient_prop' in q_args.keys() and q_args['recipe'] in ingredients:
        res_dict['question_type'] = 'ingredient_property'
        q_args['ingredients'] = [q_args['recipe']]
        del q_args['recipe']
        res_dict['args'] = q_args
        for kw in ing_composition_kw:
            if kw in q:
                res_dict['aux_info'] = kw
    elif 'renqun' in q_args.keys() or '推荐吃' in q or '推荐喝' in q:
        res_dict['question_type'] = 'crowd_constraint'
        res_dict['args'] = q_args
        res_dict['aux_info'] = '不能' if '不能' in q or '不可以' in q or '不适宜' in q or '不适合' in q or '不推荐' in q else '能'
        #res_dict['food_type'] = '菜谱' if '菜' in q or '菜谱' in q or 'recipe' in q_args.keys() or ('properties' in q_args.keys() and q_args['properties'] == '做法') else '食材'
        res_dict['food_type'] = '菜谱' if '菜' in q and ('推荐' in q or '哪些' in q) or ('吃' in q and '什么' in q and '食材' not in q) or '适合' in q and ('吃' in q or '喝' in q) or 'recipe' in q_args.keys() or 'tags' in q_args.keys() or '怎么做' in q else '食材'
    # this is the case where a recipe name could be an ingredient too ！！！！！！
    elif 'recipe' in q_args.keys() and q_args['recipe'] in ingredients and '哪' in q and '菜' in q:
        res_dict['question_type'] = 'constraint_query'
        q_args['ingredients'] = [q_args['recipe']]
        del q_args['recipe']
        res_dict['args'] = q_args
    
    #elif user['disease'] != [''] and ('吃' in q and ('推荐' in q or '菜' in q)): # or '推荐喝' in q:
    #    res_dict['question_type'] = 'crowd_constraint'
    #    res_dict['args'] = {'renqun': '{}'.format(user['disease'][0])}
    #    res_dict['aux_info'] = '能'
    #    res_dict['food_type'] = '菜谱'

    else:
        res_dict['question_type'] = 'unknown'
    return res_dict

'''
PARSING MODULE: Match the question with a template
'''
# Match the question with a template
def parser(qdict, user):
    allergies = user['allergies']
    dislikes = user['dislikes']
    #health_tags = user['disease']
    dislikes_allergies = list(filter(None, allergies+dislikes))
    query = []
    parsed_dict = {}
    aux_info = []
    qtype = qdict['question_type']
    if qtype == 'recipe_property':
        recipe = qdict['args']['recipe']
        prop = qdict['args']['properties']
        query.append(property_queries[prop].format(recipe))
    elif qtype == 'relationship_query':
        recipe = qdict['args']['recipe']
        inds = qdict['args']['ingredients']
        for ind in inds:
            query.append(relationship_query.format(recipe, ind, ind))
            aux_info.append(ind)
    elif qtype == 'ingredient_property':
        ings = qdict['args']['ingredients']
        prop = qdict['args']['ingredient_prop']
        for ing in ings:
            query.append(ingredient_queries[prop].format(ing))
            aux_info.append(ing)
    elif qtype == 'constraint_query':
        constraints = list(qdict['args'].keys())
        aux_query = constraint_queries_segments['head']
        for constraint_type in constraints:
            constraint_info = qdict['args'][constraint_type]
            if constraint_type == 'ingredients':
                for ing in constraint_info:
                    aux_query += constraint_queries_segments['ingredients'].format(ing)
                    aux_info.append(ing)
            else:
                aux_query += constraint_queries_segments[constraint_type].format(constraint_info)
            if len(dislikes_allergies) > 0:
                for ing in dislikes_allergies:
                    aux_query += constraint_queries_segments['filter'].format(ing)
        aux_query += constraint_queries_segments['tail']
        query.append(aux_query)
    elif qtype == 'crowd_constraint':
        renqun = qdict['args']['renqun']
        if qdict['food_type'] == '菜谱' and 'properties' not in qdict['args'].keys():
            #query.append(constraint_queries['tags'].format(renqun))
            aux_query = constraint_queries_segments['head']
            aux_query += constraint_queries_segments['tags'].format(renqun)
            aux_info = qdict['args']['recipe'] if 'recipe' in qdict['args'].keys() else ''
            parsed_dict['food_type'] = '菜谱'
            if 'ingredients' in qdict['args'].keys():
                for ing in qdict['args']['ingredients']:
                    #query.append(constraint_queries['ingredients'].format(ing))
                    aux_query += constraint_queries_segments['ingredients'].format(ing)
            if len(dislikes_allergies) > 0:
                for ing in dislikes_allergies:
                    aux_query += constraint_queries_segments['filter'].format(ing)
            aux_query += constraint_queries_segments['tail']
            query.append(aux_query)
        elif qdict['food_type'] == '食材' or qdict['args']['properties'] == '材料':
            for crowd_constraint_query in crowd_constraint_queries:
                query.append(crowd_constraint_query.format(renqun ,renqun))
            if 'ingredients' in qdict['args'].keys():
                aux_info = qdict['args']['ingredients']
            parsed_dict['food_type'] = '食材'
        elif 'properties' in qdict['args'].keys() and 'ingredients' in qdict['args'].keys():
            aux_query = constraint_queries_segments['head']
            if qdict['args']['properties'] == '做法':
                for ing in qdict['args']['ingredients']:
                    #query.append(constraint_queries['ingredients'].format(ing))
                    aux_query += constraint_queries_segments['ingredients'].format(ing)
            #query.append(constraint_queries['tags'].format(renqun))
            aux_query += constraint_queries_segments['tags'].format(renqun)
            if len(dislikes_allergies) > 0:
                for ing in dislikes_allergies:
                    aux_query += constraint_queries_segments['filter'].format(ing)
            aux_query += constraint_queries_segments['tail']
            query.append(aux_query)
            parsed_dict['food_type'] = '菜谱'
    #elif qtype == 'replacement_query':
    #    if 'tool' in qdict['args'].keys():
    #        tool = qdict['args']['tool']
    #        query.append(replacemet_queries['tool'].format(tool))
    #    elif 'ingredient' in qdict['args'].keys():
    #        ing = qdict['args']['ingredient'][0]
    #        query.append(replacemet_queries['ingredient'].format(ing))

    #queries = post_process_query(query, user) ###
    parsed_dict['question_type'] = qtype
    parsed_dict['queries'] = query
    parsed_dict['aux_info'] = aux_info
    return parsed_dict

'''
RETRIEVE MODULE: Retrieve the answer from a query
'''


import functools as ft
# Retrieve the answer from a query
def retrieve_query(query_info, user):
    queries = query_info['queries']
    qtype = query_info['question_type']
    dfs = []
    for i, query in enumerate(queries):
        if qtype == 'relationship_query':
            ing = query_info['aux_info'][i]
            try:
                res = kg.query_as_df(query)
                res = res.groupby(['recipe']).agg(lambda x: ', '.join(x.unique())).reset_index()
                #res['ing'] = [ing]
                res['ing'] = pd.Series([ing for x in range(len(res.index))])
                #res = res.drop_duplicates(['ing'])
                dfs.append(res)     
            except:
                if ing in all_to_one.keys():
                    query = query.replace('ind:{}'.format(ing), 'ind:{}'.format(all_to_one[ing]))
                    res = kg.query_as_df(query)
                    if not res.empty:
                        res = res.groupby(['recipe']).agg(lambda x: ', '.join(x.unique())).reset_index()
                        res['ing'] = pd.Series([ing for x in range(len(res.index))])
                        #res = res.drop_duplicates(['ing'])
                        dfs.append(res)
                    elif ing in one_to_all.keys():
                        for oname in one_to_all[ing]:
                            new_query = query.replace('ind:{}'.format(ing), 'ind:{}'.format(oname))
                            res = kg.query_as_df(new_query)
                            if not res.empty:
                                res = res.groupby(['recipe']).agg(lambda x: ', '.join(x.unique())).reset_index()
                                res['ing'] = pd.Series([ing for x in range(len(res.index))])
                                dfs.append(res)
                                break

        elif qtype == 'ingredient_property':
            res = kg.query_as_df(query)
            if res.empty:
                for ing in query_info['aux_info']:
                    if ing in all_to_one.keys():
                        query = query.replace(ing, all_to_one[ing])
                        res = kg.query_as_df(query)
                        dfs.append(res)
            else:
                dfs.append(res)
        elif qtype == 'crowd_constraint' or qtype == 'replacement_query':
            res = kg.query_as_df(query)
            dfs.append(res)
        else:
            try:
                res = kg.query_as_df(query)
                if 'prop' in res.columns:
                    res = res.groupby(['prop']).agg(lambda x: ', '.join(x.unique())).reset_index()
                elif 'recipe' in res.columns:
                    res = res.groupby(['recipe']).agg(lambda x: ', '.join(x.unique())).reset_index()
                elif 'definition' in res.columns:
                    res = res.groupby(['definition']).agg(lambda x: ', '.join(x.unique())).reset_index()
                elif res.empty:
                    res = pd.DataFrame(columns=['definition', 'recipe', 'tool', 'snba', 'data_s', 'prop'])
                dfs.append(res)
            except:
                ### 优化
                if qtype == 'constraint_query':
                    for possible_ing in query_info['aux_info']:
                        if possible_ing in ingredients and possible_ing in all_to_one.keys():
                            query = query.replace(possible_ing, all_to_one[possible_ing])
                            res = kg.query_as_df(query)
                            
                            res = res.groupby(['recipe']).agg(lambda x: ', '.join(x.unique())).reset_index()
                            dfs.append(res)
    #merging all DFs
    if qtype == 'relationship_query' and dfs != []:
        df = pd.concat(dfs, axis=0)
        # add tool filter
        df_final = df.loc[df['snba'].isin(user['sn8']) & df['data_s'].isin(user['db'])]
        if df_final.empty:
            df_final = df.drop_duplicates(['ing']) ### 优化
    elif qtype != 'ingredient_property' and qtype != 'replacement_query' and dfs != []: ## and qtype != 'recipe_property':
        if any(df.empty for df in dfs):
            df_final = pd.DataFrame()
        elif qtype == 'crowd_constraint' and query_info['food_type'] == '食材':

            df_final = pd.concat(dfs, axis=1)
        else:
            df = ft.reduce(lambda left, right: pd.merge(left, right, on=['definition', 'recipe', 'tool', 'snba', 'data_s']), dfs)
            df = df.loc[:,~df.columns.duplicated()]
            # add tool filter
            df_final = df.loc[df['snba'].isin(user['sn8']) & df['data_s'].isin(user['db'])] if df.empty != True else df
            if df_final.empty:
                df_final = df 
    elif qtype == 'unknown' or dfs == []:
        df_final = pd.DataFrame()
    # case: A和B可以一起吃吗
    elif qtype == 'ingredient_property' and len(query_info['aux_info']) > 1 and dfs != []:
        df_final = pd.concat(dfs, axis=0)
    else:
        df_final = pd.concat(dfs, axis=1)
    return df_final

'''
BEAUTIFICATION MODULE: give final answer to user
'''


def beautification_module(q_dict, df):
    qtype = q_dict['question_type']
    #try:
        #df = df_input.loc[df_input['tool'].isin(user1['tool'])]
    # if df == empty should we return any recipe or not ?
    #except:
        #df = df_input
    
    if 'definition' in df:
        aux_dict = []
        for i,row in df.iterrows():
            try:
                aux_dict.append(popularity_dict[row['definition']])
            except KeyError:
                aux_dict.append(0)
        df['pop'] = aux_dict
        df = df.sort_values(by=['pop'], ascending=False)

    
    if qtype != 'unknown':
        args = q_dict['args']
        answer = ''

        if qtype == 'recipe_property':
            recipe = args['recipe']
            answer += '制作【{}】需要：\n'.format(recipe)
            if args['properties'] == '材料':
                main = '，'.join([aux.replace('ind:', '').strip()+' (主料)' for aux in df['mainMat'].tolist()[0].split(',') if 'unk' not in aux])
                supp = '，'.join([aux.replace('ind:', '').strip()+' (辅料)' for aux in df['suppMat'].tolist()[0].split(',') if 'unk' not in aux])
                season = '，'.join([aux.replace('ind:', '').strip()+' (调料)' for aux in df['seasonMat'].tolist()[0].split(',') if 'unk' not in aux])
                answer += (main + '\n'+ supp + '\n'+ season).strip() #+ '。'
            elif args['properties'] == '主料':
                main = '，'.join([aux.replace('ind:', '').strip()+' (主料)' for aux in df['mainMat'].tolist()[0].split(',')])# if aux != 'ind:unk'])
                if 'unk' in main:
                    answer = '本食谱没有主料'
                else:
                    answer += main + '。'
            elif args['properties'] == '辅料':
                main = '，'.join([aux.replace('ind:', '').strip()+' (辅料)' for aux in df['suppMat'].tolist()[0].split(',')])# if aux != 'ind:unk'])
                if 'unk' in main:
                    answer = '本食谱没有辅料'
                else:
                    answer += main + '。'
            elif args['properties'] == '调料':
                main = '，'.join([aux.replace('ind:', '').strip()+' (调料)' for aux in df['seasonMat'].tolist()[0].split(',')])# if aux != 'ind:unk'])
                if 'unk' in main:
                    answer = '本食谱没有调料'
                else:
                    answer += main + '。'
            elif args['properties'] == '耗时':
                time = df['time'].tolist()[0]
                answer += time + '。'
            elif args['properties'] == '类型':
                tags = '，'.join([aux.strip() for aux in df['tags'].tolist()[0].split(',')])
                answer = '【{}】的类型是【{}】。'.format(recipe, tags)
            elif args['properties'] == '工艺':
                cook_method = df['method'].tolist()[0]
                answer = '【{}】的工艺是【{}】'.format(recipe, cook_method)
            elif args['properties'] == '口味':
                flavor = df['flavor'].tolist()[0]
                answer = '【{}】的口味是【{}】'.format(recipe, flavor)
            elif args['properties'] == '工具':
                tool = df['tool'].tolist()[0].strip()
                answer = '制作【{}】需要【{}】'.format(recipe, tool)
            elif args['properties'] == '难度':
                diff = df['diff'].tolist()[0].strip()
                answer = '【{}】的难度是【{}】'.format(recipe, diff)
            elif args['properties'] == '做法':  ###### 优化
                steps_list = [entry.strip() for entry in df['steps'].tolist()[0].split('\n')]
                steps_list = list(filter(None, steps_list))
                steps_dict = build_steps_dict(steps_list)
                answer =  '【{}】的做法是：\n'.format(recipe)
                for k,v in steps_dict.items():
                    answer += '第{}步：{}'.format(k, v) + '\n'
            elif args['properties'] == '适合食用':
                if 'tags' in df.columns:
                    suitable_crowd = df['tags'].tolist()[0].strip()
                    answer = '【{}】适合这些人群吃: {}'.format(recipe, suitable_crowd) ### ！！！
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                else:
                    answer = 'sorry，我现在的知识不够，还在学习中。要不换个问题试试吧！' #### LIST
            else:
                # actually, we can use the below line for almost all the properties, it's more efficient
                prop_value = df['prop'].tolist()[0].strip() ### ！！！
                answer = '【{}】的【{}】是：{}'.format(recipe, args['properties'], prop_value) if prop_value != 'unk' else '抱歉，本食谱没有【{}】信息'.format(args['properties'])
        elif qtype == 'relationship_query':
            recipe = args['recipe']
            ings = args['ingredients']
            if df.empty != True:
                for i, row in df.iterrows():
                    quantity = row['quantity']
                    ing = row['ing']
                    if quantity != 'unk':
                        answer += '需要【{}】{}\n'.format(quantity, ing)
                    else:
                        answer += '需要【适量】{}\n'.format(ing)
            else:
                answer = '【{}】不需要【{}】。'.format(recipe, ' '.join(ings))
            '''
            if df.empty != True:
                
                quantity = df['quantity'].tolist()[0]
                if quantity == 'unk':
                    answer = '需要【适量】' 
                else:
                    answer = '需要【{}】'.format(quantity)         
            else:
                answer = '【{}】不需要【{}】。'.format(recipe, ingredient)
            '''
        elif qtype == 'constraint_query' and not df.empty:
            if 'aux_info' in q_dict.keys() and q_dict['aux_info'] != '':
                rec_query = q_dict['aux_info']
                rec_list = df['definition'].tolist()
                # case tool query ?
                if rec_query in rec_list:
                    answer = '可以做【{}】'.format(rec_query)
                else:
                    answer = '没有发现证据，请自行斟酌。' 
            else:
                rec_list = df['definition'].tolist()[0:10]  ### LIMIT = 10
                if len(rec_list) > 0:
                    answer = '可以试试这些菜：\n'
                    answer += '\n'.join(rec_list)
                else:
                    answer = '没有发现证据，请自行斟酌。'
        elif qtype == 'replacement_query':
            if 'tool' in args.keys() and df.empty != True:
                tool = args['tool']
                answer = '可以用下面这些来替代【{}】: \n'.format(tool)
                for i, row in df.iterrows():
                    answer += row['repTool'] + '\n'
            elif 'ingredients' in args.keys() and df.empty != True:
                ing = args['ingredients'][0]
                answer = '可以用下面这些来替代【{}】: \n'.format(ing)
                for i, row in df.iterrows():
                    answer += row['repInd'] + '\n'
            elif df.empty == True:
                answer = '抱歉，小助手目前没有这些知识。' ### LIST
        elif qtype == 'ingredient_property':
            ingredients = args['ingredients']
            # case: A和B可以一起吃吗
            if len(ingredients) > 1 and q_dict['args']['ingredient_prop'] == '宜同食':
                # first check if these ingredients contain each other within 宜同食
                syn_ings = set()
                for ing_info in df['prop'].tolist():
                    aux = ing_info.split('\n')
                    ing_list = [ing.split()[0] for ing in aux if ing != '']
                    syn_ings.update(ing_list)
                intersec = syn_ings.intersection(set(ingredients))
                if len(intersec) == 0:
                    answer = '没有发现证据，请自行斟酌。' 
                # can add a new if and look for recipes with these ingredients, ie use a constraint query
                # elif:
                else:
                    answer = '【{}】可以一起吃'.format('，'.join(ingredients))
            # case 其他的属性
            else:
                for ingredient in ingredients:
                    if 'aux_info' in q_dict.keys():
                        composition = q_dict['aux_info']
                        comp_dict = build_ing_composition_dict(df['prop'].tolist()[0].strip())
                        if comp_dict != {} and composition in comp_dict.keys():
                            answer = '【{}】的【{}】是：'.format(ingredient, composition)
                            answer += comp_dict[composition]
                        else:
                            answer = '抱歉，小助手目前没有这些知识。' ### LIST
                    else:
                        answer = '【{}】的【{}】是：\n'.format(ingredient, args['ingredient_prop'])
                        result = df['prop'].tolist()[0].strip()
                        answer += result
                        if 'unk' in answer: answer = '没有发现证据，请自行斟酌。' #### LIST
        elif qtype == 'crowd_constraint':
            rq = args['renqun']
            ftype = q_dict['food_type']
            if  'ingredients' in args.keys() and 'recommended' in df.columns:
                recommended = [entry.replace('ind:', '') for entry in df['recommended'].dropna().unique().tolist()]
                notRecommended = [entry.replace('ind:', '') for entry in df['notRecommended'].dropna().unique().tolist()] if 'notRecommended' in df.columns else ''
                ingredient = args['ingredients'][0]
                aux_set = {'一般人群', '一般人均可', '一般人都可'}
                if ingredient in recommended:
                    answer = '【{}】可以吃【{}】'.format(rq, ingredient)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                elif ingredient in notRecommended:
                    answer = '【{}】不推荐吃【{}】'.format(rq, ingredient)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                elif '限定' in ing_constraints[ingredient].keys() and rq in ing_constraints[ingredient]['限定']:
                    answer = '【{}】不宜多吃【{}】'.format(rq, ingredient)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                elif ing_constraints[ingredient] != {} and len(aux_set.intersection(set(ing_constraints[ingredient]['推荐']))) > 0 and rq not in ing_constraints[ingredient]['不推荐']:
                    answer = '一般人群可以吃【{}】'.format(ingredient)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                else:
                    answer = '没有发现证据，请自行斟酌。' ### LIST
            elif 'recipe' in args.keys():
                recipe = args['recipe']
                recommended = [entry for entry in df['definition'].dropna().unique().tolist()] if df.empty != True else []
                # try to find exact match
                if recipe in recommended:
                    answer = '【{}】可以吃【{}】'.format(rq, recipe)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                # try to find weak match
                elif check_kw_in_recipe(recipe, recommended) != []:
                    recs = check_kw_in_recipe(recipe, recommended)[0:10] ### LIMIT = 10
                    answer = '【{}】可以吃：\n {}'.format(rq, '\n'.join(recs))
                else:
                    answer = '没有发现证据，请自行斟酌' ### recipe not in tags list (LIST)
            elif ftype == '食材':
                recommended = [entry.replace('ind:', '') for entry in df['recommended'].dropna().unique().tolist()] if 'recommended' in df.columns else ''
                notRecommended = [entry.replace('ind:', '') for entry in df['notRecommended'].dropna().unique().tolist()] if 'notRecommended' in df.columns else ''
                rec = '，'.join(recommended)
                notrec = '，'.join(notRecommended)
                if q_dict['aux_info'] == '能' and rec != '':
                    answer = '{}\n【可以吃】：\n{}'.format(rq, rec)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                elif notrec != '':
                    answer += '\n【不推荐吃】：{}'.format(notrec)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
                else:
                    answer = '没有发现证据，请自行斟酌' ##### ！！！！
            elif ftype == '菜谱' and df.empty != True:
                recommended = [entry for entry in df['definition'].dropna().unique().tolist()]
                # case where need to use tag as intersection. Ex: 粥
                if 'tags' in args.keys() and check_kw_in_recipe(args['tags'], recommended) != []:
                    recs = check_kw_in_recipe(args['tags'], recommended)[0:10] ### LIMIT = 10
                    answer = '【{}】可以吃：\n {}'.format(rq, '\n'.join(recs))
                # otherwise, display first 10 recipes 
                else:
                    rec = '\n'.join(recommended[0:10]) ### LIMIT = 10
                    answer = '【{}】可以吃: \n{}'.format(rq, rec)
                    answer += '\n*数据来源于互联网，具体情况请遵医嘱' #### ！！！！
            else:
                answer = '没有发现证据，请自行斟酌'
        else:
            answer = '没有发现证据，请自行斟酌'
    else:
        answer = '抱歉，还没明白你的意思。换个问题试试吧！'
    return answer

# getting all together
def QA_pipeline(question, user):
    # classify step (1)
    try:
        qdict = classify_question(question, user)
    except:
        return '不小心出错了[1]，换个问题试试吧'
    if qdict['question_type'] in ['recipe_property', 'relationship_query', 'constraint_query', 'ingredient_property',
                                  'crowd_constraint']:
        # parsing step (2)
        try:
            pdict = parser(qdict, user)
        except:
            return '不小心出错了[2]，换个问题试试吧'
        # retrieving step (3)
        try:
            df = retrieve_query(pdict, user)
        except:
            return '不小心出错了[3]，换个问题试试吧'
        # filtering step
        try:
            df = df.loc[df['snba'].isin(user['sn8']) & df['data_s'].isin(user['db'])]
        except:
            df = pd.DataFrame()
        if df.empty:  # ie, the user doesn't have the needed tools, return the whole df (no tool filter)
            df = retrieve_query(pdict, user)
        # beautification step (4)
        try:
            answer = beautification_module(qdict, df)
        except:
            return '不小心出错了[4]，换个问题试试吧'
        # case where we have a not useful (not informative) answer, check in FAQ
        # NOTE: uncomment in case of need
        '''
        if any(kw in answer for kw in ['Sorry', '不需要', '没有发现证据', '抱歉']) and \
                qdict['question_type'] != 'crowd_constraint':
            rec = check_recipies(question)
            answer = match_faq2(rec, question)
        '''
    elif qdict['question_type'] == 'unknown':
        rec = check_recipies(question)
        answer = match_faq2(rec, question)
    else:
        answer = '找不到答案，换个问题试试吧'
    return answer


def testing(user):
    test_queries = [q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, q11, q12, q13, q14]
    print('Running tests..')
    for q in test_queries:
        QA_pipeline(q, user)
    print('Done without errors!')

if not os.path.exists(kg_path):
    print('KG not found..')
    print('Constructing KG, this might take a while..')
    kg = construct_kg()
    print('Done!')
    # run tests
    user = {'tool': ['', '', ''], 'sn8': ['', ''], 'db': ['waibu']}
    testing(user)
    # save kg
    print('Saving KG to ', kg_path, '..')
    kg.save_rdf(kg_path, format='ttl')
    print('Done!')
else:
    print('KG found!')
    print('Loading KG, this might take a while..')
    namespaces = {
        "rcp": "https://schema.org/Recipe",
        "ind": "https://schema.org/recipeIngredient",
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "hto": "https://schema.org/HowTo",
    }
    kg = kglab.KnowledgeGraph(
        name="A recipe KG example based on 美食天下",
        base_uri="https://home.meishichina.com/",
        namespaces=namespaces,
    )
    kg = kg.load_rdf(kg_path)