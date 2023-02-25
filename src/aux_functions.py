import re
from src.check_functions import check_ingredients
from pywebio.input import *
from pywebio.output import *

# This method is specially defined to check user's question about recipes procedure (ex: 下一步，上一步，第二步，等)
# ONLY FOR WAIBU DATA
def extract_steps_properties(q):
    stepn, action, ingredient = '', '', ''
    if '第' in q and '步' in q:
        stepn = re.search(r'第(.*?)步', q).group(1)
    elif '上' in q and '步' in q:
        action = 'prev'
    elif '下' in q and '步' in q:
        action = 'next'
    elif '重' in q or '再' in q:
        action = 'repeat'
    elif check_ingredients(q) != [] and ('多少' in q or '几' in q):
        ingredient = check_ingredients(q)
    return {'state': stepn, 'action': action, 'ingredient': ingredient}


'''
MODIFY FOR NEIBU!!!
Actually can merge extract_steps_properties and extract_steps_properties2
'''

# This method is specially defined to check user's question about recipes procedure (ex: 下一步，上一步，第二步，等)
# ONLY FOR NEIBU DATA
def extract_steps_properties2(q):
    stepn, action, ingredient, stepinfo = '', '', '', ''
    if '第' in q and '步' in q:
        stepn = re.search(r'第(.*?)步', q).group(1)
    elif '上' in q and '步' in q:
        action = 'prev'
    elif '下' in q and '步' in q:
        action = 'next'
    elif '重' in q or '再' in q:
        action = 'repeat'
    elif check_ingredients(q) != [] and ('多少' in q or '几' in q):
        ingredient = check_ingredients(q)

    # below is info needed only for neibu data
    if '模式' in q:
        stepinfo = '模式'
    elif '哪一层' in q or '几层' in q or '层位' in q:
        stepinfo = '层位'
    elif '预热温度' in q or '预热' in q:
        stepinfo = '预热温度'
    elif '温馨提示' in q or '小技巧' in q:
        stepinfo = '温馨提示'
    elif '食材份量' in q:
        stepinfo = '食材份量'
    elif '食材' in q or '材料' in q:
        stepinfo = '食材名称'
    elif '步骤描述' in q or '步骤' in q or '描述' in q or '操作' in q:
        stepinfo = '步骤描述'
    elif '设备' in q or '工具' in q or '厨具' in q:
        stepinfo = '设备类型'
    return {'state': stepn, 'action': action, 'ingredient': ingredient, 'step_info': stepinfo}

# Transform a step list-like to a dictionary. [1. 准备材料，2. 切土豆，...] --> {1: 准备材料, 2: 切土豆, ...}
def build_steps_dict(steps_list):
    max_step = len(steps_list) + 1
    stepn = 1
    steps_dict = dict()
    for entry in steps_list:
        if stepn != max_step:
            text = entry.replace(str(stepn), '', 1)
            steps_dict[stepn] = text
            stepn += 1
    return steps_dict

# Do the inverse of "build_steps_dict" method
def decode_steps(steps_text):
    steps_dict = dict()
    for step in steps_text.strip().split('\n')[1:]:
        stepn = re.search(r'第(.*?)步', step).group(1)
        text = step.split('第{}步：'.format(stepn))[-1]
        steps_dict[int(stepn)] = text
    return steps_dict

# aux function to build ingredient composition dict from the composition information (ex, 热量，维生素C, 等)
def build_ing_composition_dict(composition_string):
    composition_dict = dict()
    for entry in composition_string.split('\n'):
        if len(entry) > 0 and entry != 'unk':
            splits = entry.split('\xa0')
            comp = splits[0]
            value = splits[1]
            composition_dict[comp] = value
    return composition_dict

# generate user information (now only supporting tools)
def generate_user():
    user_dict = {}
    tools = input('家里有什么厨具？\n')
    user_dict['tool'] = tools.split()
    user_dict['sn8'] = ['']
    return user_dict

# generate web user information
def generate_web_user():
    user_dict = {}
    #allergies = input('您有什么过敏吗？如：虾，蟹 \n')
    #dislikes = input('您有什么忌口吗？ 如：青菜，胡萝卜 \n')
    #disease = input('您有什么慢性疾病吗？如：糖尿病，高血压')
    allergies = textarea("您有什么过敏吗？", placeholder="如：虾，蟹", required=False)
    dislikes = textarea("您有什么忌口吗？", placeholder="如：青菜，胡萝卜", required=False)
    #disease = select('您有什么养生的需求吗？', help_text='可以不选', options=recipe_renqun_tags, multiple=True)
    
    user_dict['allergies'] = [allergies]
    user_dict['dislikes'] = [dislikes]
    #user_dict['disease'] = disease
    return user_dict

recipe_renqun_tags = ['延缓衰老', '壮腰健肾', '补肾', '补气', '疏肝理气', '补血', '解酒', '活血化瘀', '便秘', '清热解毒',
                '养肝', '益智补脑', '气血双补', '通乳', '补心', '止血调理', '祛痰', '增肥', '明目', '健忘', '减肥',
                '产后调理', '哺乳期', '贫血', '补虚养身', '利尿', '痛经']

fixed_tags = ['孕妇', '产妇', '幼儿', '哺乳期', '婴儿', '学龄前儿童', '学龄期儿童', '青少年', '老人',
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

# For testing purpose
q1 = '凉拌酸辣土豆片需要用那些材料'    # recipe property
q2 = '春笋百叶结的做法'          # recipe property  -----
q3 = '青椒炒腊肉要多少土豆'      # relationship query
q4 = '番茄鸡蛋要多少盐'         # relationship query
q5 = '清淡热菜有哪些'           # constraint query
q6 = '用五花肉的菜有哪些'         # constraint query
q7 = '土豆的宜同食'            # ingredient property
q8 = '土豆和什么菜好搭配'          # ingredient property
q9 = '土豆的禁忌人群'              # ingredient property
q10 = '孕妇能吃河虾吗？'            # crowd constraint (ingredient)
q11 = '孕妇能吃牛奶炖蛋吗'           # crowd constraint (recipe)
q12 = '高血压患者能吃哪些食材？'        # crowd constraint
q13 = '我要减肥，推荐吃哪些菜'        # crowd constraint
q14 = '适合老人吃的茄子怎么做'      # crowd constraint

filter_ing = """FILTER NOT EXISTS {{  ?recipe rcp:allMats "{}" .}}"""
filter_health_condition = """?recipe rcp:recipeTags "{}" .\n """

def post_process_query(queries, user):
    allergies = user['allergies']
    dislikes = user['dislikes']
    #health_tags = user['disease']
    dislikes_allergies = list(filter(None, allergies+dislikes))
    new_query = ''
    new_query_list = []
    for query in queries:
        splits = query.split('}\n')
        new_query += splits[0]
        #if health_tags != ['']:
        #    for health_tag in health_tags:
        #        new_query += filter_health_condition.format(health_tag)
        if len(dislikes_allergies) > 0:
            for ing in dislikes_allergies:
                new_query += filter_ing.format(ing)
        new_query += '}'
        new_query_list.append(new_query)
    return new_query_list