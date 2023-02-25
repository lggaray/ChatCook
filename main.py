import re
from src.modules import QA_pipeline as QA_loop
from src.modules import kg
from src.question_matching import match_faq2
from src.check_functions import check_recipies, one_to_all, neibu_unique_recipes
from src.aux_functions import extract_steps_properties, extract_steps_properties2, decode_steps
from data.templates.neibu_queries import data_source_query, neibu_step_query, neibu_query
from pycnnum import cn2num
from datetime import datetime


# inner loop for recipe steps
# ONLY FOR WAIBU DATA
def inner_loop(recipe, user):
    #recipe = check_recipies(recipe)
    materials = QA_loop('{}需要准备哪些材料'.format(recipe), user)
    tool = QA_loop('{}的工具'.format(recipe), user)
    steps = QA_loop('{}的步骤'.format(recipe), user)
    steps_dict = decode_steps(steps)
    #print('首先需要准备下面这些材料：')
    ans = ''
    for mat in materials.strip().split('\n')[1:]:
        for m in mat.split('，'):
            if m != '。' and m != '':
                m = m.split(' (')[0]
                quantity = QA_loop('{}需要多少{}'.format(recipe, m), user)
                quantity = re.search(r'【(.*?)】', quantity).group(1)
                if quantity == recipe or quantity == 'unk':
                    ans += m + ' ' + '适量' + '\n'
                else:
                    ans += m + ' ' + quantity + '\n'
    print('[{}]'.format(str(datetime.now()).split('.')[0]) + '【答】： 首先需要准备下面这些材料：\n' + ans)
    ans = '还需要准备：' + re.findall(r'【(.*?)】', tool)[-1] + '\n'
    print(ans)
    ans = '第一步：' + steps_dict[1]
    print(ans)
    #print('还需要准备：', re.findall(r'【(.*?)】', tool)[-1], '\n')
    #print('您可以给我说：“下一步”， “上一步”， “重复一下”， 或者直接说 “第n步”')
    #print('第一步：', steps_dict[1])
    global_stepn = 1
    while global_stepn != max(steps_dict.keys()):
        step_question = input("请输入您的问题：")
        # !!!!
        process_question = '[{}]'.format(str(datetime.now()).split('.')[0]) + '【问】：' + step_question
        print(process_question)
        step_prop = extract_steps_properties(step_question)
        if step_prop['state'] != '':
            stepn = step_prop['state']
            stepn = cn2num(stepn)
            if stepn > 0 and stepn <= max(steps_dict.keys()):
                ans = '第{}步：{}'.format(stepn, steps_dict[stepn])
                global_stepn = stepn
            else:
                ans = '抱歉，没有第{}步。'.format(stepn)
        elif step_prop['action'] == 'next':
            if global_stepn != max(steps_dict.keys()):
                global_stepn += 1
                ans = '第{}步：{}'.format(global_stepn, steps_dict[global_stepn])
            else:
                ans = '抱歉，没有下一步。'
        elif step_prop['action'] == 'prev':
            if global_stepn != 1:
                global_stepn -= 1
                ans = '第{}步：{}'.format(global_stepn, steps_dict[global_stepn])
            else:
                ans = '抱歉，没有上一步。'
        elif step_prop['action'] == 'repeat':
            ans = '第{}步：{}'.format(global_stepn, steps_dict[global_stepn])
        elif '退出' in step_question:
            break
        else:
            step_question = recipe + step_question if recipe not in step_question else step_question
            ans = QA_loop(step_question, user)
        # case where we have a not useful (not informative) answer, check in FAQ
        if any(kw in ans for kw in ['Sorry', '不需要', '没有发现证据', '抱歉']):
            ans = match_faq2(recipe, step_question)
        process_answer = '[{}]'.format(str(datetime.now()).split('.')[0]) + '【答】：' + ans
        print(process_answer)
    if global_stepn == max(steps_dict.keys()):
        print('【答】：辛苦了！菜谱已经完成了，慢慢吃。')

# ONLY FOR NEIBU DATA
def inner_loop2(recipe, user):
    query = neibu_query.format(recipe)
    df = kg.query_as_df(query)
    df = df.loc[df['snba'].isin(user['sn8'])]
    if df.empty:
        # in case any recipe fullfil the criteria
        df = kg.query_as_df(query)
        # select the first recipe
        rec_id = df['recipe'].tolist()[0]
        step_count = df['step_count'].tolist()[0]
    else:
        # there's an UNIQUE recipe that fullfil the criteria
        rec_id = df['recipe'].tolist()[0]
        step_count = df['step_count'].tolist()[0]

    # now iterate over the recipe information
    step_info_dicts = {}
    for i in range(step_count):
        query = neibu_step_query.format(rec_id, i + 1)
        df = kg.query_as_df(query)
        df_dict = df.to_dict('records')
        step_info_dicts[i + 1] = df_dict[0]

    # give user a list of needed materials
    #print('首先需要准备下面这些材料：')
    ans = ''
    for k, v in step_info_dicts.items():
        if v['食材名称'] != 'unk':  # ！！！
            ans += '{}：{}\n'.format(v['食材名称'], v['食材份量']) # print('{}：{}'.format(v['食材名称'], v['食材份量']))
    print('首先需要准备下面这些材料：' + ans)
    # present only first step and then go into a loop
    #print('\n第1步：')
    ans = ''
    for k, v in step_info_dicts[1].items():
        if v != 'unk':
            ans += '【{}】: {}'.format(k, v)  # print('【{}】: {}'.format(k, v))
    #print()
    print('第1步：' + ans)
    global_stepn = 1
    # in this loop the user can ask anything about this recipe
    while global_stepn != max(step_info_dicts.keys()):
        step_question = input("请输入您的问题：")
        step_prop = extract_steps_properties2(step_question)
        # question style '第n步'
        if step_prop['state'] != '' and step_prop['step_info'] == '':
            stepn = step_prop['state']
            stepn = cn2num(stepn)
            if stepn > 0 and stepn <= max(step_info_dicts.keys()):
                ans = '第{}步：'.format(stepn)
                for k, v in step_info_dicts[stepn].items():
                    if v != 'unk':
                        ans += '【{}】：{}'.format(k, v)
                global_stepn = stepn
                #print() ###
            else:
                ans = '抱歉，没有第{}步。'.format(stepn)
        # question style '下一步'
        elif step_prop['action'] == 'next' and step_prop['step_info'] == '':
            if global_stepn != max(step_info_dicts.keys()):
                global_stepn += 1
                ans = '第{}步：'.format(global_stepn)
                for k, v in step_info_dicts[global_stepn].items():
                    if v != 'unk':
                        ans += '【{}】：{}'.format(k, v)
                #print() ###
            else:
                ans = '抱歉，没有下一步。'
        # question style '上一步'
        elif step_prop['action'] == 'prev' and step_prop['step_info'] == '':
            if global_stepn != 1:
                global_stepn -= 1
                ans = '第{}步：'.format(global_stepn)
                for k, v in step_info_dicts[global_stepn].items():
                    if v != 'unk':
                        ans += '【{}】：{}'.format(k, v)
                #print() ###
            else:
                ans = '抱歉，没有上一步。'
        # question style '重复步骤'
        elif step_prop['action'] == 'repeat' and step_prop['step_info'] == '':
            ans = '第{}步：'.format(global_stepn)
            for k, v in step_info_dicts[global_stepn].items():
                if v != 'unk':
                    ans += '【{}】：{}'.format(k, v)
            print() ###
        # below is a question specific to a n step, for example: '第n步的食材份量'
        elif step_prop['step_info'] != '':
            aux_step_n = 0
            step_property = step_prop['step_info']
            if step_prop['state'] != '':
                aux_step_n = step_prop['state']
                aux_step_n = cn2num(aux_step_n)
            elif step_prop['action'] == 'prev':
                aux_step_n = global_stepn - 1
            elif step_prop['action'] == 'next':
                aux_step_n = global_stepn + 1
            if 0 < aux_step_n <= max(step_info_dicts.keys()):
                step_info = step_info_dicts[aux_step_n][step_property]
                if step_info != 'unk':
                    ans = '第{}步的【{}】：{}'.format(aux_step_n, step_property, step_info)
                else:
                    ans = '抱歉，第{}步没有{}。'.format(aux_step_n, step_property)
            elif step_info_dicts[global_stepn][step_property] != 'unk':
                step_info = step_info_dicts[global_stepn][step_property]
                ans = '【{}】：{}'.format(step_property, step_info)
            elif step_info_dicts[global_stepn][step_property] == 'unk':
                ans = '抱歉，本食谱没有【{}】信息'.format(step_property)
            else:
                ans = '抱歉，没有第{}步。'.format(aux_step_n)
        # another way of asking ingredient quantity but outside the scope of a step
        elif step_prop['ingredient'] != '':
            query_ings = step_prop['ingredient']
            ans = ''
            for query_ing in query_ings:
                for k, v in step_info_dicts.items():
                    if query_ing == v['食材名称']:
                        ans += '【{}】需要【{}】\n'.format(query_ing, v['食材份量'])
                        break
                    elif query_ing in one_to_all.keys():
                        for oname in one_to_all[query_ing]:
                            if oname == v['食材名称']:
                                ans += '【{}】需要【{}】\n'.format(oname, v['食材份量'])
                                break
            if ans == '':
                ans = '不需要{}'.format(query_ing)
                #print(ans)
            #else:
                #print('不需要{}'.format(query_ing))
        # key-word for quiting the loop
        elif '退出' in step_question:
            break
        # last attempt to answer user's question outside the scope of this particular recipe
        else:
            step_question = recipe + step_question if recipe not in step_question else step_question
            ans = QA_loop(step_question, user)
        # case where we have a not useful (not informative) answer, check in FAQ
        if any(kw in ans for kw in ['Sorry', '不需要', '没有发现证据', '抱歉']):
            ans = match_faq2(recipe, step_question)
        print(ans)
    if global_stepn == max(step_info_dicts.keys()):
        print('辛苦了！菜谱已经完成了，慢慢吃。')

#user = {'tool': ['', '', ''], 'sn8': ['0'], 'db': ['waibu']}
user = {'tool': ['', '', ''], 'sn8': ['', '']}
#data_source = input('请选数据库来源：内部（写 neibu）或者 外部（写waibu）：')

def chatbot():
    unsolved_questions = []
    #user = generate_user()
    data_source = 'neibu'  #input('请选数据库来源：内部（写 neibu）或者 外部（写waibu）：', required=True)
    #print('data source: ', data_source)
    user['db'] = [data_source]
    while True:
        question = input("请输入您的问题：")
        process_question = '[{}]'.format(str(datetime.now()).split('.')[0]) + ' 【问】：' + question
        print(process_question)
        with open('questions_answer.txt', 'a') as f:
            f.write('\n')
            f.write(process_question + '\n')
            if ('带我做' in question or '教我做' in question) and check_recipies(question) != '':
                rec = check_recipies(question)
                # 内部数据
                if data_source == 'neibu' and rec in neibu_unique_recipes:
                    inner_loop2(rec, user)
                    process_answer = '[{}]'.format(str(datetime.now()).split('.')[0]) + 'inner_loop2'
                # 外部数据
                else:
                    user['sn8'] = ['0']
                    try:
                        inner_loop(rec, user)
                        process_answer = '[{}]'.format(str(datetime.now()).split('.')[0]) + ' inner_loop'
                    except:
                        process_answer = '[{}]'.format(str(datetime.now()).split('.')[0]) + ' 不小心出错了[5]，换个问题试试吧'
            elif '谢谢' in question or '退出' in question:
                print('【答】：' + '再见！')
                break
            else:
                answer = QA_loop(question, user)
                if type(answer) == tuple:
                    print(answer)
                    answer = answer[2]
                process_answer = '[{}]'.format(str(datetime.now()).split('.')[0]) + ' 【答】：' + \
                                 answer.replace('【', '').replace('】', '')
                print(process_answer)
            f.write(process_answer)
            f.write('\n')
    return unsolved_questions

if __name__ == '__main__':
    unsolved_questions = chatbot()
    if unsolved_questions:
        print(unsolved_questions)
        file_name = str(datetime.now()).replace(' ', '_').split('.')[0]
        with open('unsolved_questions_{}.txt'.format(file_name), 'w') as f:
            for unsolved in unsolved_questions:
                f.write(unsolved+'\n')
