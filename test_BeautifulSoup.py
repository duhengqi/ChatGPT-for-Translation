from bs4 import BeautifulSoup

def modify_html(html_string, tag_name, replacement_text):
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_string, 'html.parser')

    # 找到所有指定标签
    target_tags = soup.find_all(tag_name)

    # 替换标签内容为指定文本
    for tag in target_tags:
        # if tag.string is not None:
        #   tag.string += str("\n\n\n"+ replacement_text)
        if tag.contents[0] is not None:
           tag.contents[0] += str("\n"+ replacement_text)
           print(tag.contents[0])
    # 获取修改后的HTML
    modified_html = str(soup)
    return modified_html

with open("D:/oscode/ChatGPT-for-Translation/af_xdp.html", "r", encoding='utf-8') as f:
    text = f.read()
# print(text)
# 替代所有<p>标签的内容为指定字符串
modified_html = modify_html(text, 'p', 'Replacement Text')
with open("D:/oscode/ChatGPT-for-Translation/test.html", "w", encoding='utf-8') as f:
    text = f.write(modified_html)
# print(modified_html)
