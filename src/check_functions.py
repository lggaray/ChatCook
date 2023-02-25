import re
import spacy
import pandas as pd
import pickle

nlp = spacy.load("zh_core_web_sm")

'''
LOAD DATA
'''

# ingredients_df = pd.read_csv('data/all_ingredients.csv')
# ingredients_df = ingredients_df.fillna('unk')
ingredients_df = pd.read_excel('data/complemented_full_merged_ings.xlsx')


# open dictionaries
with open('data/dicts/cooking_methods.txt', 'r') as f:
    cooking_methods = f.readlines()

with open('data/dicts/cooking_times.txt', 'r') as f:
    cooking_times = f.readlines()

with open('data/dicts/flavors.txt', 'r') as f:
    flavors = f.readlines()

with open('data/dicts/main_mat.txt', 'r') as f:
    main_mat = f.readlines()

with open('data/dicts/supp_mat.txt', 'r') as f:
    supp_mat = f.readlines()

with open('data/dicts/season_mat.txt', 'r') as f:
    season_mat = f.readlines()

with open('data/dicts/all_ingredients.txt', 'r') as f:
    ingredients = f.readlines()

with open('data/dicts/recipes.txt', 'r') as f:
    recipes = f.readlines()

with open('data/dicts/tags.txt', 'r') as f:
    tags = f.readlines()

with open('data/dicts/tools.txt', 'r') as f:
    tools = f.readlines()

with open('data/dicts/difficulty.txt', 'r') as f:
    difficulty = f.readlines()

with open('data/dicts/neibu_unique_recipes.txt', 'r') as f:
    neibu_unique_recipes = f.readlines()

recipes = [entry.strip() for entry in recipes]
neibu_unique_recipes = [entry.replace('\n', '') for entry in neibu_unique_recipes]
ingredients = [entry.strip() for entry in ingredients]
cooking_methods = [entry.strip() for entry in cooking_methods]
tools = [entry.strip() for entry in tools]


# ingredient name [one to all]
with open('data/one_to_all.pickle', 'rb') as handle:
    one_to_all = pickle.load(handle)

# complement info
one_to_all['排骨'].add('肋排') #### ！

# ingredient name [all to one]
with open('data/all_to_one.pickle', 'rb') as handle:
    all_to_one = pickle.load(handle)

# Recipe properties with keywords
property_qwds = {'做法': ['做法', '怎么做', '步骤'],
                  '口味': ['口味','味道'],
                  '工艺': ['工艺'],
                  '耗时': ['多久','耗时', '多长时间'],
                  '工具': ['工具', '厨具', '设备'],
                  '材料': ['食材', '食料', '材料', '用料', '原料'],
                  '主料': ['主料', '主食'],
                  '辅料': ['辅料'],
                  '调料': ['调料'],
                  '难度': ['难度', '难不难', '容易', '难做'],
                  '类型': ['类型', '分类'],
                  '层位': ['哪一层', '几层', '层位'],
                  '模式': ['模式', '烤模式', '烤箱模式', '微波炉模式'],
                  '预热温度': ['预热温度', '温度预热'],
                  '温馨提示': ['温馨提示', '小技巧']
                   }

property_qwds_set = set()
for k,v in property_qwds.items():
    property_qwds_set.add(k)
    property_qwds_set.update(set(v))

# Ingredient composition related keywords
ing_composition_kw = ['叶酸', '尼克酸', '核黄素', '烟酸', '热量', '生物素', '硒', '硫胺素', '碘', '碘 ', '碳水化合物',
                          '磷', '纤维素', '维生素A', '维生素B1', '维生素B12', '维生素B2', '维生素B6', '维生素C', '维生素C ',
                          '维生素D', '维生素E', '胆固醇', '胡罗卜素', '胡萝卜素', '能量', '脂肪', '膳食纤维', '营养素 ',
                          '蛋白质', '钙', '钠', '钾', '铁', '铁毫', '铜', '锌', '锌 ', '锌毫', '锰', '镁', '镁毫', '食物纤维']

# Ingredient health related keywords
health_qwds = {'宜同食': ['宜同食', '搭配', '配', '一起吃'],
                 '忌同食': ['忌同食', '不能搭配'],
                 '营养价值': ['营养价值', '营养', '价值', '什么用', '帮助', '好处'],
                 '食用功效': ['食用功效', '功效'],
                 '适用人群': ['适用人群', '适用'],
                 '禁忌人群': ['禁忌人群', '禁忌', '禁'],
                 '营养成分': ['营养成分', '成分'] + ing_composition_kw,
                 '简介': ['简介', '介绍', '食材简介'],
                 '选购技巧': ['选购技巧', '怎么买'],
                 '存储': ['如何保存', '怎么保存', '存储'],
                }

health_qwds_set = set()
for k,v in health_qwds.items():
    health_qwds_set.add(k)
    health_qwds_set.update(set(v))

# Crowd constraint related keywords
renqun_list = ['孕妇', '产妇', '幼儿', '哺乳期', '婴儿', '学龄前儿童', '学龄期儿童', '青少年', '老人',
       '高温环境作业人群', '低温环境作业人群', '接触电离辐射人员', '接触化学毒素人员', '运动员', '围孕期',
       '前列腺', '糖尿病', '高血压', '高血脂', '冠心病', '中风', '消化性溃疡', '肠炎', '防癌抗癌',
       '胆石症', '肝硬化', '肾炎', '痛风', '麻疹', '结核病', '肝炎', '动脉硬化', '甲状腺', '胃炎',
       '贫血', '痔疮', '月经不调', '子宫脱垂', '痛经', '更年期', '小儿遗尿', '营养不良', '咽炎',
       '关节炎', '跌打骨折损伤', '骨质疏松', '耳鸣', '肺气肿', '口腔溃疡', '尿路结石', '支气管炎', '术后',
       '美容', '减肥', '延缓衰老', '消化不良', '神经衰弱', '乌发', '补虚养身', '补阳壮阳', '滋阴补肾',
       '壮腰健肾', '清热解毒', '夜尿多', '产后调理', '不孕不育', '明目', '健脾开胃', '防暑', '脚气',
       '益智补脑', '肢寒畏冷', '祛痰', '通乳', '清热去火', '头痛', '解酒', '增肥', '补心', '养肝',
       '补脾', '养肺', '补肾', '补气', '补血', '气血双补', '哮喘', '感冒', '腹泻', '癫痫', '水肿',
       '便秘', '失眠', '健忘', '利尿', '活血化瘀', '止血调理', '疏肝理气', '心悸', '痢疾', '呕吐',
       '阳痿早泄', '自汗盗汗', '胃调养', '咳喘']

# Extended words for crowd constraint queries
extended_renqun_words = {
    '老人': ['老年人', '长者','长辈','老头','老头儿', '老者','年龄大的人','老头子'],
    '孕妇': ['怀孕者', '妊娠', '怀孕', '孕期', '产前', '孕前期','孕中期','孕后期'],
    '产妇' : ['围产期','生孩子后','生完孩子','产后','哺乳期','喂奶'],
    '幼儿': ['儿童', '孩子', '小孩子', '稚童', '娃娃', '小娃', '小孩', '小朋友', '小孩儿', '娃', '小学'],
    '贫血': ['血红蛋白低', '缺血', '缺铁', '血蛋白低', '血色素低'],
    '高血压' : ['血压高', '降血压'],
    '糖尿病' : ['血糖高', '高血糖', '消渴症', '降血糖'],
    '青少年' : ['高中', '初中', '中学', '少年人'],
    '湿热体质' : ['湿气重', '易上火', '虚热', '湿热'],
    '气虚体质' : ['气虚','补气','补气血', '补血气','气血双补', '体虚'],
    '痰湿体质' : ['痰湿', '湿痰'],
    '便秘' : ['大便干', '排便困难', '大便出不来','拉不出来'],
    '减肥': ['肥胖','减肥','减脂','减重','瘦身'],
    '营养不良' : ['营养差','缺营养','营养不行','营养不好','补充营养','补营养','改善营养'],
    '癌症患者' : ['癌', '肿瘤', '白血病'],
    '阴虚体质' : ['阴虚'],
    '更年期' : ['绝经'],
    '水肿' : ['浮肿']
}
extended_renqun_words = { v: k for k, l in extended_renqun_words.items() for v in l }

extended_tag_words = {
    '早餐': ['早上', '早饭'],
    '午餐': ['中午', '午饭'],
    '晚餐': ['晚上', '晚饭'],
    '快手菜': ['方便', '新手'],
    '清淡': ['平淡'],
    '增重增肌': ['锻炼', '健身'],
    '健康食谱': ['健康'],
    '餐后点心': ['点心'],
    '热汤': ['汤'],
    '减肥瘦身': ['减肥', '瘦身']
}

suitable_crowd = ['什么人', '什么样的人', '啥人', '啥样的人']

# difference between different sets to avoid misclassification
recipes = set(recipes) - set(flavors) - set(tags) - set(cooking_methods) - set(tools) \
    - set(renqun_list) - health_qwds_set - property_qwds_set - set(['面', '饭', '午餐', '早餐'])  # 面, 汤 are too broad 
ingredients = set(ingredients) - set(flavors) - set(tags) - set(cooking_methods) - set(tools) \
    - set(renqun_list) - health_qwds_set - property_qwds_set
main_mat = set(main_mat) - set(flavors) - set(tags) - set(cooking_methods) - set(recipes) - set(tools) \
    - set(renqun_list) - health_qwds_set - property_qwds_set
supp_mat = set(supp_mat) - set(flavors) - set(tags) - set(cooking_methods) - set(recipes) - set(tools) \
    - set(renqun_list) - health_qwds_set - property_qwds_set
season_mat = set(season_mat) - set(flavors) - set(tags) - set(cooking_methods) - set(recipes) - set(tools) \
    - set(renqun_list) - health_qwds_set - property_qwds_set


# second round of cleaning ingredients to avoid misclassification
bad_ing = {'颜', '无', '白', '黄', '他', '错', '加水', '糊锅', '小', '柿子', '低筋', '角', '红色', '勾芡', '勺子', '瓜', '温',
           '水适量', '筷子', '薯', '蛋', '红', '主料', '主', '戚风', '蛋糕', '', '饭', '糖醋排骨', '粥', '时间', '腌',  '烤红薯',
           '烤鸡翅', '烤盘', '盘子', '温度', '其他', '面', '皮', '香', '蛋挞', '汤'}
ingredients = set(ingredients) ^ bad_ing
ingredients = ingredients.union(set(['盐', '香葱', '牛油果']))
## cooking_methods.append('扎孔').append('抹') ###
action_words = ['扎孔', '抹', '反面', '去皮', '去血', '去骨', '摆', '间距', '最多', '至少']

for k, v in one_to_all.items():
    for oname in v:
        if oname not in ingredients and oname != '':
            ingredients.add(oname)

'''
DEFINE CHECK FUNCTIONS
'''
# extract cooking method from question, output = 'cooking_method'
def check_cooking_method(q):
    recipe = check_recipies(q)
    res = ''
    for entry in cooking_methods:
        cooking_method = entry.replace('\n', '')
        if cooking_method in q.replace(recipe, ''):  #check the cooking method is not part of the recipe name
            res = cooking_method
    return res

# extract action words or words related to actions from question, output = 'action_word'
def check_action_words(q):
    a = ''
    for action in action_words:
        if action.strip() in q:
            a = action.strip()
    return a

# extract tags name from question, output = 'tag_name'
def check_tags(q):
    res = ''
    for entry in tags:
        tag = entry.replace('\n', '')
        if tag in q:
            res = tag
    if res == '':
        for k, v in extended_tag_words.items():
            for tag_oname in v:
                if tag_oname in q:
                    res = k
                    break
    return res

# extract flavor name from question, output = 'flavor_name'
def check_flavors(q):
    recipe = check_recipies(q)
    res = ''
    for entry in flavors:
        flavor = entry.replace('\n', '')
        if flavor in q.replace(recipe, ''): #check the flavor is not part of the recipe name
            res = flavor
    return res

# extract recipe  property from question, output = 'recipe_property'
def check_properties(q):
    res = ''
    for k, v in property_qwds.items():
        for prop in v:
            if prop in q:
                res = k
    return res

# extract ingredient health property from question, output = 'health_property'
def check_health_prop(q):
    res = ''
    for k, v in health_qwds.items():
        for prop in v:
            if prop in q:
                res = k
    return res

# extract main material name from question, output = 'main_material'
def check_main_mat(q):
    recipe = check_recipies(q)
    res = ''
    for entry in main_mat:
        ingredient = entry.replace('\n', '')
        if ingredient in q.replace(recipe, ''): #check the ingredient is not part of the recipe name
            res = ingredient
    return res

# extract supplement material name from question, output = 'supplement_material'
def check_supp_mat(q):
    recipe = check_recipies(q)
    res = ''
    for entry in supp_mat:
        ingredient = entry.replace('\n', '')
        if ingredient in q.replace(recipe, ''): #check the ingredient is not part of the recipe name
            res = ingredient
    return res

# extract seasoning material name from question, output = 'seasoning_material'
def check_season_mat(q):
    recipe = check_recipies(q)
    res = ''
    for entry in season_mat:
        ingredient = entry.replace('\n', '')
        if ingredient in q.replace(recipe, ''): #check the ingredient is not part of the recipe name
            res = ingredient
    return res

# extract difficulty level from question, output = 'diffculty'
def check_difficulty(q):
    recipe = check_recipies(q)
    res = ''
    for entry in difficulty:
        level = entry.replace('\n', '')
        if level in q.replace(recipe, ''):
            res = level
    return res


def check_ingr_type(ingr):
    ingr_type = dict()
    if check_main_mat(ingr) != '':
        ingr_type = '主料'
    elif check_supp_mat(ingr) != '':
        ingr_type = '辅料'
    elif check_season_mat(ingr) != '':
        ingr_type = '调料'
    return ingr_type


# extract recipe name from question based in POS (used in check_recipies)
def extract_recipe_name(txt):
    recipe_name = ''
    for i, token in enumerate(nlp(txt)):
        # check for NOUN and make sure is not a property
        if token.pos_ == 'NOUN' and token.text not in property_qwds:
            recipe_name += token.text
        # check for VERB and make sure it's between NOUNS or PROPN (or maybe hardcode 炒?)
        elif token.pos_ == 'VERB' and i != 0 and i != len(nlp(txt)) - 1:
            if (nlp(txt)[i-1].pos_ == 'NOUN' or nlp(txt)[i-1].pos_ == 'PROPN') and (nlp(txt)[i+1].pos_ == 'NOUN' or
                                                                                    nlp(txt)[i-1].pos_ == 'PROPN'):
                recipe_name += token.text
        # check for PROPN
        elif token.pos_ == 'PROPN':
            recipe_name += token.text
    return recipe_name

# extract recipe name from question, output = 'recipe_name'
def check_recipies(q):
    res_list = ['']
    extracted_name = extract_recipe_name(q)
    # first try to match every recipe in the recipes list with the question
    for recipe in recipes:
        #recipe = recipe.replace('\n', '')
        if recipe in q:
            res_list.append(recipe)
    # otherwise extract recipe name from question and match with the recipes list
    if extracted_name in recipes:
        res_list.append(extracted_name)
    else:
        oname_rec = recursive_lookup(extracted_name)
        if oname_rec == '' and '炒' in extracted_name: #  didn't find A炒B ? Try with B炒A
            splits = extracted_name.split('炒')
            inv_name = splits[-1] + '炒' + splits[0]
            oname_rec = recursive_lookup(inv_name)
        res_list.append(oname_rec)
    res_list = sorted(res_list, key=lambda x: (-len(x), x)) # sort by max length
    return res_list[0]

# aux function to specifically capture possible ingredients separated in two due to the tokenizer
# (ex: (低筋, 面粉) ---> 低筋面粉)
# now only supporting NOUN + NOUN case and only returning the first pair 【!】
def complete_ing_name(q):
    out = ''
    for i, token in enumerate(nlp(q)):
        if (i < len(nlp(q)) - 2) and token.pos_ == 'NOUN' and nlp(q)[i + 1].pos_ == 'NOUN' and \
                nlp(q)[i + 2].pos_ == 'NOUN':
            out = token.text + nlp(q)[i + 1].text + nlp(q)[i + 2].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'NOUN' and nlp(q)[i + 1].pos_ == 'NOUN':
            out = token.text + nlp(q)[i + 1].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'NOUN' and nlp(q)[i + 1].text == '馍蛋':
            out = token.text + nlp(q)[i + 1].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'ADJ' and nlp(q)[i + 1].pos_ == 'NOUN':
            out = token.text + nlp(q)[i + 1].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'ADJ' and nlp(q)[i + 1].pos_ == 'PROPN':
            out = token.text + nlp(q)[i + 1].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'NUM' and nlp(q)[i + 1].pos_ == 'NOUN':
            out = token.text + nlp(q)[i + 1].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'NOUN' and nlp(q)[i + 1].text == '清':
            out = token.text + nlp(q)[i + 1].text
        elif (i < len(nlp(q)) - 1) and token.pos_ == 'VERB' and nlp(q)[i + 1].text == '油果':
            out = token.text + nlp(q)[i + 1].text
    return out

# extract ingredient names from question, output = [ing1, ing2, ..]
def check_ingredients(q):
    aux_list = []
    ing_list = []

    for ing in ingredients:
        if ing in q:
            aux_list.append(ing)

    aux_list = sorted(aux_list, key=lambda x: (-len(x), x))
    for possible_ing in aux_list:
        if possible_ing in q:
            q = q.replace(possible_ing, '')
            ing_list.append(possible_ing)
        elif possible_ing in all_to_one.keys() and all_to_one[possible_ing] in q:
            q = q.replace(all_to_one[possible_ing], '')
            ing_list.append(all_to_one[possible_ing])

    return ing_list

# extract crowd name from question, output = 'crowd_name'
def check_renqun(q):
    tag = check_tags(q)
    renqun = ''
    if tag in renqun_list:
        renqun = tag
        q = q.replace(tag, '')
    else:
        for rq in renqun_list:
            if rq in q:
                renqun = rq
                q = q.replace(rq, '')
        if renqun == '':
            for k in extended_renqun_words.keys():
                if k in q:
                    renqun = extended_renqun_words[k]
                    q = q.replace(k, '')
                    break
    return [q, renqun]

# extract recipe names with a specific keyword, like 汤，粥，等等
def check_kw_in_recipe(kw, rec_list):
    out = []
    for recipe in rec_list:
        if kw in recipe:
            out.append(recipe)
    return out

# recursive lookup defined to use in recipe name detection
def recursive_lookup(recipe_name):
    # 鸡蛋炒番茄
    res = ''
    for token in nlp(recipe_name):
        if token.pos_ == 'NOUN' or token.pos_ == 'PROPN':
            try:
                for oname_ingr in one_to_all[token.text]:
                    oname_rec = recipe_name.replace(token.text, oname_ingr)
                    if oname_rec in recipes:
                        res = oname_rec
                        break
            except:
                pass
    return res

replaceble_keywords = ['必须是', '必须用', '是必须', '可以换', '可以用', '一定要', '行不行', '换成', '可以做吗', '可以吗', '也可以用来做']
importance_keywords = ['可以不用', '可以不放', '可以不加', '可以不用', '行不行', '不加可以', '不加', '不放', '不用加', '不放可以']
purpose_keywords = ['为什么要用', '为什么要放', '为啥要用', '为啥要放', '为啥要加', '为什么要加']
execution_keywords = ['做得对吗', '做的对吗']
tool_specific_keywords = ['哪一层', '多少度', '加热', '几分钟']
ingredient_specific_keywords = ['哪里买的', '牌子', '哪儿买的', '泡多久', '多大', '放多了']

def check_tools(q):
    t = ''
    for tool in tools:
        if tool.strip() in q:
            t = tool.strip()
    return t

# Ingredient/Tool
def check_x_replaceble(q):
    out = dict()
    if ('没' in q and '可以做' in q) or ('没' in q and '放什么' in q) or ('没' in q and '怎么办' in q) or \
            ('没' in q and '可以吗' in q) or ('用' in q and '行吗' in q) or ('可以' in q and '代替' in q) or \
            ('可以' in q and '替代' in q) or ('没有' in q and '能做吗' in q) or ('可以用' in q and '做吗' in q):
        if check_tools(q) != '':
            out['tool'] = check_tools(q)
        elif check_ingredients(q) != []:
            out['ingredient'] = check_ingredients(q)
    else:
        for kw in replaceble_keywords:
            if kw in q and check_tools(q) != '':
                out['tool'] = check_tools(q)
            elif kw in q and check_ingredients(q) != []:
                out['ingredient'] = check_ingredients(q)
    return out

# Ingredient
def check_x_importance(q):
    out = dict()
    if ('不放' in q and '可以' in q) or ('没有' in q and '可以' in q) or ('不放' in q and '怎样' in q) or \
            ('不放' in q and '怎么样' in q) or ('不放' in q and '影响味道吗' in q) or ('不加' in q and '影响味道吗' in q) or \
            ('不用' in q and '影响味道吗' in q):
        if check_ingredients(q) != []:
            out['ingredient'] = check_ingredients(q)
    else:
        for kw in importance_keywords:
            if kw in q and check_ingredients(q) != []:
                out['ingredient'] = check_ingredients(q)
    return out

# Ingredient
def check_x_purpose(q):
    out = dict()
    for kw in purpose_keywords:
        if kw in q and check_ingredients(q) != []:
            out['ingredient'] = check_ingredients(q)
    return out

def check_execution(q):
    out = False
    if ('我做的' in q and '为什么' in q) or ('放多了' in q and '怎么' in q):
        out = True
    else:
        for kw in execution_keywords:
            if kw in q:
                out = True
    return out

def check_tool_specific(q):
    out = False
    for kw in tool_specific_keywords:
        if kw in q and check_tools(q) != '':
            out = True
    return out

def check_ingredient_specific(q):
    out = dict()
    if check_ingredients(q) != []:
        if ('新鲜的' in q and '怎么处理' in q) or ('新鲜的' in q and '可以' in q) or ('生的' in q and '可以' in q) or \
                ('生的' in q and '放进去' in q) or ('生的' in q and '操作' in q):
            out['ingredient'] = check_ingredients(q)
        else:
            for kw in ingredient_specific_keywords:
                if kw in q:
                    out['ingredient'] = check_ingredients(q)
    return out


# optimized
def check_all(q):
    dic = dict()
    # first clean possible noise for the parser
    q = q.replace('多少', '').replace('少', '')
    recipe = check_recipies(q)
    if recipe:
        dic['recipe'] = recipe
        q = q.replace(recipe, '')#.replace(extract_recipe_name(q), '')
    renqun = check_renqun(q)[1]
    if renqun:
        dic['renqun'] = renqun
        q = check_renqun(q)[0]
    ingredients = check_ingredients(q)
    if ingredients:
        dic['ingredients'] = ingredients
        for ing in ingredients:
            q = q.replace(ing, '')
    flavor = check_flavors(q)
    if flavor:
        dic['flavor'] = flavor
        q = q.replace(flavor, '')
    health_prop = check_health_prop(q)
    if health_prop:
        dic['ingredient_prop'] = health_prop
        q = q.replace(health_prop, '')
    recipe_prop = check_properties(q)
    if recipe_prop:
        dic['properties'] = recipe_prop
        q = q.replace(recipe_prop, '')
    tool = check_tools(q)
    if tool:
        dic['tool'] = tool
        q = q.replace(tool, '')
    cooking_method = check_cooking_method(q)
    if cooking_method:
        dic['cooking_method'] = cooking_method
        q = q.replace(cooking_method, '')
    tag = check_tags(q)
    if tag:
        dic['tags'] = tag
        q = q.replace(tag, '')
    difficulty = check_difficulty(q)
    if difficulty:
        dic['difficulty'] = difficulty
        q = q.replace(difficulty, '')
    if 'recipe' in dic.keys() and len(dic.keys()) == 1 and any(ele in q for ele in suitable_crowd) == True:
        dic['properties'] = '适合食用'
    return dic

# modify check_all for FAQ pipeline
def check_all_FAQ(q):
    dic = dict()
    ingredients = check_ingredients(q)
    if ingredients:
        dic['ingredients'] = ingredients
        for ing in ingredients:
            q = q.replace(ing, '')
    tool = check_tools(q)
    if tool:
        dic['tool'] = tool
        q = q.replace(tool, '')
    action = check_action_words(q)
    if action:
        dic['action_words'] = action
        q = q.replace(action, '')
    return dic