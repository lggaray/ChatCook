import kglab
import json
import re
import pickle
import rdflib
import pandas as pd
import numpy as np
from collections import defaultdict
from fuzzywuzzy import process, fuzz
from src.check_functions import main_mat, supp_mat, season_mat
from src.aux_functions import fixed_tags


'''
LOAD DATA
'''
# recipes
recipes_df = pd.read_csv('data/all_recipes.csv')
recipes_df = recipes_df.sort_values(by=['收藏'], ascending=False)
recipes_df = recipes_df.fillna('unk')

# ingredients
#ingredients_df = pd.read_csv('data/all_ingredients.csv')
#ingredients_df = ingredients_df.fillna('unk')

ingredients_df = pd.read_excel('data/complemented_full_merged_ings.xlsx')
ingredients_dict = ingredients_df.set_index('食材名').T.to_dict('dict')
choices = ingredients_df['食材名'].tolist()

# expand ingredient's dict
ingredients_dict_expanded = {}
for ing in ingredients_dict.keys():
    # other names
    if '[' in ing:
        splits = ing.split('[')
        onames = splits[1].split(',')
        ingredients_dict_expanded[splits[0]] = ingredients_dict[ing]
        for name in onames:
            ingredients_dict_expanded[name] = ingredients_dict[ing]
    # specific information
    elif '(' in ing and ('均值' in ing or '标准' in ing):
        splits = ing.split('(')
        ingredients_dict_expanded[splits[0]] = ingredients_dict[ing]
    else:
        ingredients_dict_expanded[ing] = ingredients_dict[ing]

# load ingredient constraints
with open('data/crowd_constraint.pickle', 'rb') as handle:
    ing_constraints = pickle.load(handle)

# load ingredient matching name (merged ing vs all ing)
with open('data/ing_name_matching_dict.pickle', 'rb') as handle:
    ing_matching_dict = pickle.load(handle)

# tools
tools_df = pd.read_excel('data/tools.xlsx')
tools_df = tools_df.drop('Unnamed: 0', axis=1)

tool_replacement = defaultdict(list)
for i, row in tools_df.iterrows():
    if not isinstance(row['替换方法'], float):
        tool_replacement[row['工具名'].split('（')[0]] = [entry.split('、')[-1] for entry in row['替换方法'].split('\n')]


popularity_dict = dict()
for i, row in recipes_df.iterrows():
    popularity_dict[row['菜谱名']] = row['收藏']

# neibu data
neibu1 = pd.read_excel('data/neibu/菜谱数据2022-05-13_14_40_41.xlsx')
neibu2 = pd.read_excel('data/neibu/菜谱数据2022-05-13_14_43_58-副本.xlsx')
neibu3 = pd.read_excel('data/neibu/菜谱数据2022-05-13_14_45_58.xlsx')

pdList = [neibu1, neibu2, neibu3]
neibu_df = pd.concat(pdList)
neibu_df.菜谱ID = neibu_df.菜谱ID.astype(str)

neibu_df = neibu_df.fillna('unk')
neibu_df.预热温度 = neibu_df.预热温度.astype(str)

# delete duplicates
neibu_df = neibu_df.replace('[外销]', '')
unique_recipes_df = neibu_df.drop_duplicates(['菜谱ID']) ##########
#unique_recipes_df = neibu_df.drop_duplicates(['菜谱名称'])

'''
Clean 主料/辅料/调料 names

input: ingredients cell from df
output: list of tuples in the form (ingredient, quantity)
'''
def clean_material_names(mat_info):
    ing_quantity_list = []
    for ind_plus_quantity in mat_info.strip().split('\n'):
        ind = ind_plus_quantity.split()[0]
        q = ind_plus_quantity.split()[-1]
        if '、' in ind:
            inds = ind.split('、')
            for ind in inds:
                try:
                    ind = re.sub('\W+', ' ', ind).split()[0]
                    ing_quantity_list.append((ind, q))
                except:
                    ing_quantity_list.append((inds[0], q))
        else:
            ind = re.sub('\W+', '', ind)
            ind = re.sub('\d+', '', ind)
            ing_quantity_list.append((ind, q))
    return ing_quantity_list


'''
Match neibu ingredients with meishitianxia ingridients
'''
def match_ing_name(neibu_ing):
    res_list = ['']
    for db_ing in ingredients_dict.keys():
        if db_ing in neibu_ing:
            res_list.append(db_ing)
    res_list = sorted(res_list, key=lambda x: (-len(x), x)) # sort by max length
    return res_list[0]


'''
CONSTRUCT GRAPH
'''
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

recipes_sample = recipes_df.sample(20, random_state=42)

def construct_kg_meishitianxia():
    # Iterate over the rows in the dataframe, representing a recipe in the KG for each row
    for index, row in recipes_df.iterrows():
        # for index, row in recipes_sample.iterrows():
        uri = row['网址']
        node = rdflib.URIRef(uri)
        kg.add(node, kg.get_ns("rdf").type, kg.get_ns("schema").Recipe)

        recipe_name = row['菜谱名'].strip()
        kg.add(node, kg.get_ns("skos").definition, rdflib.Literal(recipe_name))

        ### recipe 别名
        recipe_oname = ''
        kg.add(node, kg.get_ns("rcp").oname, rdflib.Literal(recipe_oname))

        cook_time = row["耗时"]
        kg.add(node, kg.get_ns("rcp").cookTime, rdflib.Literal(cook_time))

        cooking_method = row['烹饪工艺']
        kg.add(node, kg.get_ns("rcp").cookingMethod, rdflib.Literal(cooking_method))

        difficulty = row['难度']
        kg.add(node, kg.get_ns("rcp").difficulty, rdflib.Literal(difficulty))

        flavor = row['口味']
        kg.add(node, kg.get_ns("rcp").recipeFlavor, rdflib.Literal(flavor))

        popularity = row['收藏']
        kg.add(node, kg.get_ns("rcp").recipePopularity, rdflib.Literal(popularity))

        cooking_tools = row['工具']
        for tool in re.split(r'[^\w]', cooking_tools.strip()):
            kg.add(node, kg.get_ns("rcp").cookingTool, rdflib.Literal(tool))
            if tool in tool_replacement.keys():
                for v in tool_replacement[tool]:
                    kg.add(rdflib.Literal(tool), kg.get_ns("rcp").toolReplacement, rdflib.Literal(v))

        tags = row['分类']
        for tag in tags.strip().split('\n'):
            kg.add(node, kg.get_ns("rcp").recipeTags, rdflib.Literal(tag))
            if tag in fixed_tags:
                kg.add(node, kg.get_ns("rcp").suitableCrowd, rdflib.Literal(tag))

        ind_list = row["主料及份量"]
        if not isinstance(ind_list, float):
            cleaned_tuples = clean_material_names(ind_list)
            for tup in cleaned_tuples:
                ind = tup[0]
                quantity = tup[1]

                # define ingredient node
                ind_obj = eval('kg.get_ns("ind").{}'.format(ind))
                kg.add(node, ind_obj, rdflib.Literal(quantity))
                # add ingredient node
                kg.add(node, kg.get_ns("rcp").mainMaterial, ind_obj)
                kg.add(node, kg.get_ns("rcp").allMats, rdflib.Literal(ind))
                # add nutrient information
                ingredient_dict = ingredients_dict_expanded[ind] if ind in ingredients_dict_expanded.keys() else \
                    ingredients_dict[process.extractOne(ind, choices, scorer=fuzz.token_set_ratio)[0]]
                #if matched_ing in ingredients_dict.keys():
                for k, v in ingredient_dict.items():
                    kg.add(ind_obj, eval('kg.get_ns("ind").{}'.format(k)), rdflib.Literal(v))
                # add crowd constraint
                try:
                    keyichi = list(filter(None, ing_constraints[ind]['推荐']))
                    bukeyichi = list(filter(None, ing_constraints[ind]['不推荐']))
                    for renqun in keyichi:
                        kg.add(ind_obj, kg.get_ns("ind").isRecommendedFor, rdflib.Literal(renqun))
                    for renqun in bukeyichi:
                        kg.add(ind_obj, kg.get_ns("ind").notRecommendedFor, rdflib.Literal(renqun))
                except:
                    pass

        ind_list = row["辅料及份量"]
        if not isinstance(ind_list, float):
            cleaned_tuples = clean_material_names(ind_list)
            for tup in cleaned_tuples:
                ind = tup[0]
                quantity = tup[1]

                ind_obj = eval('kg.get_ns("ind").{}'.format(ind))
                kg.add(node, kg.get_ns("rcp").suppMaterial, ind_obj)
                kg.add(node, ind_obj, rdflib.Literal(quantity))
                kg.add(node, kg.get_ns("rcp").allMats, rdflib.Literal(ind))

                ingredient_dict = ingredients_dict_expanded[ind] if ind in ingredients_dict_expanded.keys() else \
                    ingredients_dict[process.extractOne(ind, choices, scorer=fuzz.token_set_ratio)[0]]
                #if matched_ing in ingredients_dict.keys():
                for k, v in ingredient_dict.items():
                    kg.add(ind_obj, eval('kg.get_ns("ind").{}'.format(k)), rdflib.Literal(v))

                try:
                    keyichi = list(filter(None, ing_constraints[ind]['推荐']))
                    bukeyichi = list(filter(None, ing_constraints[ind]['不推荐']))
                    for renqun in keyichi:
                        kg.add(ind_obj, kg.get_ns("ind").isRecommendedFor, rdflib.Literal(renqun))
                    for renqun in bukeyichi:
                        kg.add(ind_obj, kg.get_ns("ind").notRecommendedFor, rdflib.Literal(renqun))
                except:
                    pass

        ind_list = row["调料及份量"]
        if not isinstance(ind_list, float):
            cleaned_tuples = clean_material_names(ind_list)
            for tup in cleaned_tuples:
                ind = tup[0]
                quantity = tup[1]

                ind_obj = eval('kg.get_ns("ind").{}'.format(ind))
                kg.add(node, kg.get_ns("rcp").seasoning, ind_obj)
                kg.add(node, ind_obj, rdflib.Literal(quantity))
                kg.add(node, kg.get_ns("rcp").allMats, rdflib.Literal(ind))

                ingredient_dict = ingredients_dict_expanded[ind] if ind in ingredients_dict_expanded.keys() else \
                    ingredients_dict[process.extractOne(ind, choices, scorer=fuzz.token_set_ratio)[0]]
                #if matched_ing in ingredients_dict.keys():
                for k, v in ingredient_dict.items():
                    kg.add(ind_obj, eval('kg.get_ns("ind").{}'.format(k)), rdflib.Literal(v))

                try:
                    keyichi = list(filter(None, ing_constraints[ind]['推荐']))
                    bukeyichi = list(filter(None, ing_constraints[ind]['不推荐']))
                    for renqun in keyichi:
                        kg.add(ind_obj, kg.get_ns("ind").isRecommendedFor, rdflib.Literal(renqun))
                    for renqun in bukeyichi:
                        kg.add(ind_obj, kg.get_ns("ind").notRecommendedFor, rdflib.Literal(renqun))
                except:
                    pass

        recipe_steps = row['步骤']
        kg.add(node, kg.get_ns("hto").step, rdflib.Literal(recipe_steps))

        # ------------------- additional info ----------------------------
        kg.add(node, kg.get_ns("rcp").dataSource, rdflib.Literal('waibu'))
        kg.add(node, kg.get_ns("rcp").internalSN8, rdflib.Literal('0'))

    return kg

def construct_kg_neibu_data(kg):

    neibu_dict = unique_recipes_df.to_dict('records')  # before: neibu_df.to_dict('records')

    #### iterate over different recipes #####
    for row in neibu_dict:
        if True: #row['菜谱名称'] not in recipes_df['菜谱名'].tolist():
            # ----------------- recipe ID -------------------------------
            uri = str(row['菜谱ID'])
            node = rdflib.URIRef(uri)
            kg.add(node, kg.get_ns("rdf").type, kg.get_ns("schema").Recipe)

            # ----------------- recipe name -------------------------------
            recipe_name = clean_material_names(row['菜谱名称'])[0][0]
            #if ' ' in recipe_name:
            #    continue
            kg.add(node, kg.get_ns("skos").definition, rdflib.Literal(recipe_name))

            ### recipe 别名
            recipe_oname = ''
            kg.add(node, kg.get_ns("rcp").oname, rdflib.Literal(recipe_oname))

            # ---------------- cooking time info ---------------------------
            # join 准备时间 and 制作时间
            prep_time = row["准备时间"]
            cook_time = row["制作时间"]
            h1, h2 = prep_time.split('时')[0], cook_time.split('时')[0]
            m1, m2 = prep_time.split('时')[1].split('分')[0], cook_time.split('时')[1].split('分')[0]
            # s1, s2 = prep_time.split('时')[1].split('分')[1].split('秒')[0], cook_time.split('时')[1]
            # .split('分')[1].split('秒')[0]
            h = int(h1) + int(h2)
            m = int(m1) + int(m2)
            # s = int(s1) + int(s1)
            aux_h, aux_m = divmod(m, 60)  # minutes mod 60 (transform minutes to hours if m>60)
            # kg.add(node, kg.get_ns("rcp").cookTime, rdflib.Literal('{}时{}分{}秒'.format(str(h + aux_h),
            # str(aux_m), str(s))))
            if h + aux_h != 0:
                kg.add(node, kg.get_ns("rcp").cookTime, rdflib.Literal('{}时{}分'.format(str(h + aux_h), str(aux_m))))
            else:
                kg.add(node, kg.get_ns("rcp").cookTime, rdflib.Literal('{}分'.format(str(aux_m))))

            # ---------------- cooking method info ----------------------------
            cooking_methods = row['烹饪方式'].strip().split(',')
            for cooking_method in cooking_methods:
                kg.add(node, kg.get_ns("rcp").cookingMethod, rdflib.Literal(cooking_method))

            # ---------------- difficulty level info -------------------------
            difficulty = row['难易程度']
            if '1星' in difficulty or '2星' in difficulty:
                kg.add(node, kg.get_ns("rcp").difficulty, rdflib.Literal('简单'))
            elif '3星' in difficulty:
                kg.add(node, kg.get_ns("rcp").difficulty, rdflib.Literal('普通'))
            elif '4星' in difficulty:
                kg.add(node, kg.get_ns("rcp").difficulty, rdflib.Literal('高级'))
            else:
                kg.add(node, kg.get_ns("rcp").difficulty, rdflib.Literal('神级'))

            # ---------------- flavor info ----------------------------
            flavorss = row['口味']
            for flavor in flavorss.split(','):
                kg.add(node, kg.get_ns("rcp").recipeFlavor, rdflib.Literal(flavor))

            # ---------------- popularity info ----------------------
            popularity = 0
            kg.add(node, kg.get_ns("rcp").recipePopularity, rdflib.Literal(popularity))

            # ----------------- cooking tool info --------------------
            cooking_tools = row['设备类型']
            for tool in re.split(r'[^\w]', cooking_tools.strip()):
                kg.add(node, kg.get_ns("rcp").cookingTool, rdflib.Literal(tool))
                if tool in tool_replacement.keys():
                    for v in tool_replacement[tool]:
                        kg.add(rdflib.Literal(tool), kg.get_ns("rcp").toolReplacement, rdflib.Literal(v))

            # ------------------- tag info --------------------------
            tag1 = row['标签'].strip().replace('/', ',').split(',')
            tag2 = row['菜系'].strip().split(',')
            tag3 = row['菜式'].strip().split(',')
            tag4 = row['季节'].strip().split(',')
            tag5 = row['场景'].strip().split(',')
            tags = tag2 + tag3 + tag4 + tag5
            for tag in tags:
                if tag != 'unk' and tag != '其他':
                    kg.add(node, kg.get_ns("rcp").recipeTags, rdflib.Literal(tag))

            #### iterate over same recipe but different ingredient/steps #####
            steps = ''
            step_count = 0
            for i, row2 in neibu_df.loc[neibu_df['菜谱ID'] == uri].iterrows():
                # ------------ ingredient + quantity & ingredient property + crowd constraint info -----------
                # need to replace () because is not allowed in entities name
                mat = row2['食材名称']
                if mat != '':
                    mat = mat.replace('⅓', '')
                    mat = clean_material_names(mat)[0][0]
                    # print('aa' + mat + 'aa')
                    try:
                        ind_obj = eval('kg.get_ns("ind").{}'.format(mat))
                    except:
                        # print(row2['食材名称'])
                        pass
                    kg.add(node, kg.get_ns("rcp").allMats, rdflib.Literal(mat))
                    # print(ind_obj)
                    if mat in main_mat:
                        kg.add(node, kg.get_ns("rcp").mainMaterial, ind_obj)
                    elif mat in supp_mat:
                        kg.add(node, kg.get_ns("rcp").suppMaterial, ind_obj)
                    elif mat in season_mat:
                        kg.add(node, kg.get_ns("rcp").seasoning, ind_obj)
                    else:
                        kg.add(node, kg.get_ns("rcp").mainMaterial, ind_obj)
                        kg.add(node, kg.get_ns("rcp").suppMaterial, rdflib.Literal('unk'))
                        kg.add(node, kg.get_ns("rcp").seasoning, rdflib.Literal('unk'))

                    quantity = row2['食材份量']
                    kg.add(node, ind_obj, rdflib.Literal(quantity))

                    ingredient_dict = ingredients_dict_expanded[mat] if mat in ingredients_dict_expanded.keys() else \
                        ingredients_dict[process.extractOne(mat, choices, scorer=fuzz.token_set_ratio)[0]]
                    #if matched_ing in ingredients_dict.keys():
                    for k, v in ingredient_dict.items():
                        kg.add(ind_obj, eval('kg.get_ns("ind").{}'.format(k)), rdflib.Literal(v))

                        # add ingredient's crowd constraints 【MAYBE THIS NEED TO CHANGE IN THE FUTURE,
                        # with new crowd constraint data】
                        try:
                            keyichi = list(filter(None, ing_constraints[mat]['推荐']))
                            bukeyichi = list(filter(None, ing_constraints[mat]['不推荐']))
                            for renqun in keyichi:
                                kg.add(ind_obj, kg.get_ns("ind").isRecommendedFor, rdflib.Literal(renqun))
                            for renqun in bukeyichi:
                                kg.add(ind_obj, kg.get_ns("ind").notRecommendedFor, rdflib.Literal(renqun))
                        except:
                            pass

                    # merging step info
                    if row2['步骤序号'] != 'unk':
                        steps += str(int(row2['步骤序号']))
                        steps += row2['步骤描述']
                        steps += '\n'

                    # adding separated step info
                    if row2['步骤序号'] != 'unk':
                        step_n = int(row2['步骤序号'])
                        step_count += 1

                        step_obj = eval('kg.get_ns("hto").step{}hasIng'.format(step_n))
                        step_ing = row2['食材名称']
                        kg.add(node, step_obj, rdflib.Literal(step_ing))

                        step_obj = eval('kg.get_ns("hto").step{}hasIngQuantity'.format(step_n))
                        step_ing_quantity = row2['食材份量']
                        kg.add(node, step_obj, rdflib.Literal(step_ing_quantity))

                        step_obj = eval('kg.get_ns("hto").step{}hasOvenLevel'.format(step_n))
                        step_oven_level = row2['层位']
                        kg.add(node, step_obj, rdflib.Literal(step_oven_level))

                        step_obj = eval('kg.get_ns("hto").step{}hasOvenMode'.format(step_n))
                        step_oven_mode = row2['模式']
                        kg.add(node, step_obj, rdflib.Literal(step_oven_mode))

                        step_obj = eval('kg.get_ns("hto").step{}hasOvenPreheat'.format(step_n))
                        step_oven_preheat = row2['预热温度']
                        kg.add(node, step_obj, rdflib.Literal(step_oven_preheat))

                        step_obj = eval('kg.get_ns("hto").step{}hasTool'.format(step_n))
                        step_tool = row2['设备类型']
                        kg.add(node, step_obj, rdflib.Literal(step_tool))

                        step_obj = eval('kg.get_ns("hto").step{}hasDescription'.format(step_n))
                        step_description = row2['步骤描述'].replace('_x000D_', '')
                        kg.add(node, step_obj, rdflib.Literal(step_description))

                        step_obj = eval('kg.get_ns("hto").step{}hasTip'.format(step_n))
                        step_tip = row2['温馨提示'].replace('_x000D_', '')
                        kg.add(node, step_obj, rdflib.Literal(step_tip))

            # ---------------------- steps info -------------------------
            kg.add(node, kg.get_ns("hto").step, rdflib.Literal(steps))
            kg.add(node, kg.get_ns("hto").stepCount, rdflib.Literal(step_count))

            # --------------------- internal info -----------------------
            aux = row['语言']
            kg.add(node, kg.get_ns("rcp").internalRecipeLanguage, rdflib.Literal(aux))

            aux = row['菜谱录入时间']
            kg.add(node, kg.get_ns("rcp").internalTimeCreated, rdflib.Literal(aux))

            aux = row['简介']
            kg.add(node, kg.get_ns("rcp").internalRecipeIntroduciton, rdflib.Literal(aux))

            aux = row['   SN8   ']
            kg.add(node, kg.get_ns("rcp").internalSN8, rdflib.Literal(aux))

            aux = row['市场型号']
            kg.add(node, kg.get_ns("rcp").internalMarketModel, rdflib.Literal(aux))

            aux = row['产品型号']
            kg.add(node, kg.get_ns("rcp").internalProductModel, rdflib.Literal(aux))

            aux = row['产品编码']
            kg.add(node, kg.get_ns("rcp").internalProductCode, rdflib.Literal(aux))

            aux = row['层位']
            kg.add(node, kg.get_ns("rcp").internalFloor, rdflib.Literal(aux))

            aux = row['模式']
            kg.add(node, kg.get_ns("rcp").internalMode, rdflib.Literal(aux))

            aux = row['预热温度']
            kg.add(node, kg.get_ns("rcp").internalPreheat, rdflib.Literal(aux))

            aux = row['温馨提示']
            kg.add(node, kg.get_ns("rcp").internalTips, rdflib.Literal(aux))

            # ------------------- additional info ----------------------------
            kg.add(node, kg.get_ns("rcp").dataSource, rdflib.Literal('neibu'))

    return kg

def construct_kg():
    kg = construct_kg_meishitianxia()
    construct_kg_neibu_data(kg)
    return kg
