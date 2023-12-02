
import html5lib
with open("/code/ChatGPT-for-Translation/af_xdp.html", "rb") as f:
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder("dom"))
    document = parser.parse(f)
print("lxml")