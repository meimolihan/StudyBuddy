"""阶段3 缺口排查：找出页面模板里用到、但 CSS 里缺规则的可点击元素。
用法: python check_missing_ui.py
思路：把各页面模板的 class/id 抽出来，与 style.css 里出现过的选择器比对，
     只报告「模板在用、CSS 完全没有」的类——这才是真缺口。
     （有定义但样式不理想的另说，那是覆盖问题不是缺失。）
"""
import re
import os

TPL = r'C:\Users\meimo\Desktop\StudyBuddy\internal\web\templates'
CSS = r'C:\Users\meimo\Desktop\StudyBuddy\internal\web\static\style.css'

css = open(CSS, encoding='utf-8').read()
# 取出 CSS 里所有出现过的类名与 id 名
css_classes = set(re.findall(r'\.([A-Za-z][\w-]*)', css))
css_ids = set(re.findall(r'#([A-Za-z][\w-]*)', css))

PAGES = {
    'study.html': '学习主页',
    'textbook.html': '教材详情页',
    'quiz.html': '刷题页',
    'result.html': '结果页',
    'game.html': '游戏页',
    'archive.html': '归档页',
    'textbooks.html': '教材仓库',
    'lesson.html': '课程页',
    'partials.html': '公共组件',
}

INTERACTIVE = re.compile(r'<(button|a\b|input|select|textarea|summary)\b', re.I)

for fn, label in PAGES.items():
    p = os.path.join(TPL, fn)
    if not os.path.exists(p):
        continue
    html = open(p, encoding='utf-8').read()
    missing_c, missing_i = set(), set()
    # 只在交互标签的class 上做检查，避免把纯展示容器当缺口
    for m in INTERACTIVE.finditer(html):
        tag = html[m.start():html.find('>', m.start()) + 1]
        for c in re.findall(r'class="([^"]+)"', tag):
            for name in c.split():
                if name not in css_classes:
                    missing_c.add(name)
        for i in re.findall(r'id="([^"]+)"', tag):
            if i not in css_ids:
                missing_i.add(i)
    print('%-16s(%s)' % (fn, label))
    print('   可交互元素上CSS 无规则的 class: %s' % (sorted(missing_c) or '无'))
    print('   可交互元素上 CSS 无规则的 id  : %s' % (sorted(missing_i) or '无'))
    print()