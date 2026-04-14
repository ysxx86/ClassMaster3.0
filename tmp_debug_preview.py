import sys
sys.path.append(r'd:\ClassMaster2.2')
from utils.comment_processor import generate_preview_html
class Dummy:
    pass
Dummy.is_admin = True
Dummy.class_id = None
res = generate_preview_html(None, Dummy())
print(res.get('status'))
print(type(res.get('html')))
print(res.get('html')[:200])
