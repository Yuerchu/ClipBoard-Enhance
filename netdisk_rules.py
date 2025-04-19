# 网盘规则定义
NETDISK_RULES = {
    'baidu': {
        'name': '百度网盘',
        'reg': r'(?:https?:\/\/)?(?:[^\/\s]*?)?(?:pan|yun|eyun)\.baidu\.com\/(?:s\/[\w~-]+|share\/\S{4,}|doc\/share\/\S+)',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4})',
        'open_with_pwd': '{url}#pwd={pwd}'
    },
    'aliyun': {
        'name': '阿里云盘',
        'reg': r'(?:https?:\/\/)?(?:www\.)?(?:aliyundrive\.com\/s|alipan\.com\/s|alywp\.net)\/[a-zA-Z\d-]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4,6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'lanzou': {
        'name': '蓝奏云',
        'reg': r'(?:https?:\/\/)?(?:[a-zA-Z\d\-.]+)?(?:lanzou[a-z]|lanzn|lanzoux?)\.com\/(?:[a-zA-Z\d_\-]+|\w+\/\w+)',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{3,6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    '123pan': {
        'name': '123云盘',
        'reg': r'(?:https?:\/\/)?(?:www\.)?123pan\.com\/s\/[\w-]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4,6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'tianyi': {
        'name': '天翼云盘',
        'reg': r'(?:https?:\/\/)?cloud\.189\.cn\/(?:t\/|web\/share\?code=)?[a-zA-Z\d]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?(?:\s*|\()?([a-zA-Z0-9]{4,6})(?:\))?',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'quark': {
        'name': '夸克网盘',
        'reg': r'(?:https?:\/\/)?pan\.quark\.cn\/s\/[a-zA-Z\d-]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4,6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'weiyun': {
        'name': '腾讯微云',
        'reg': r'(?:https?:\/\/)?share\.weiyun\.com\/[a-zA-Z\d]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'caiyun': {
        'name': '移动云盘',
        'reg': r'(?:https?:\/\/)?(?:caiyun\.139\.com\/[mw]\/i(?:\?|\/)|caiyun\.139\.com\/front\/#\/detail\?linkID=)[a-zA-Z\d]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4})',
        'open_with_pwd': '{url}&pwd={pwd}'
    },
    'xunlei': {
        'name': '迅雷云盘',
        'reg': r'(?:https?:\/\/)?pan\.xunlei\.com\/s\/[a-zA-Z\d_-]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    '360': {
        'name': '360云盘',
        'reg': r'(?:https?:\/\/)?(?:yunpan\.360\.cn\/surl_[\w]+|[\w\.]+\.link\.yunpan\.360\.cn\/lk\/surl_[\w]+)',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?(?:\s*|\()?([a-zA-Z0-9]{4})(?:\))?|#([a-zA-Z0-9]{4})',
        'open_with_pwd': '{url}#{pwd}'
    },
    '115': {
        'name': '115网盘',
        'reg': r'(?:https?:\/\/)?115\.com\/s\/[a-zA-Z\d]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4})',
        'open_with_pwd': '{url}#{pwd}'
    },
    'cowtransfer': {
        'name': '奶牛快传',
        'reg': r'(?:https?:\/\/)?cowtransfer\.com\/s\/[a-zA-Z\d-]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4,6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'ctfile': {
        'name': '城通网盘',
        'reg': r'(?:https?:\/\/)?(?:[\w-]+\.)?ctfile\.com\/(?:f|d)\/\d+-\d+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?(?:\s*|\()?(\d{4})(?:\))?',
        'open_with_pwd': '{url}?p={pwd}'
    },
    'flowus': {
        'name': 'FlowUs息流',
        'reg': r'(?:https?:\/\/)?flowus\.cn\/[\w-]+\/share\/[\w-]+',
        'pwd_reg': r'',  # 通常不需要提取码
        'open_with_pwd': '{url}'
    },
    'mega': {
        'name': 'Mega网盘',
        'reg': r'(?:https?:\/\/)?mega\.nz\/(?:#!|file\/)[a-zA-Z\d!#_-]+',
        'pwd_reg': r'',  # 特殊加密方式，不使用常规提取码
        'open_with_pwd': '{url}'
    },
    'weibo': {
        'name': '新浪微盘',
        'reg': r'(?:https?:\/\/)?vdisk\.weibo\.com\/(?:s\/|lc\/)[a-zA-Z\d]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([A-Z0-9]{4})',
        'open_with_pwd': '{url}?pwd={pwd}'
    },
    'wenshushu': {
        'name': '文叔叔',
        'reg': r'(?:https?:\/\/)?(?:www\.)?wenshushu\.cn\/(?:box|f)\/[\w-]+',
        'pwd_reg': r'(?:提取|访问|密)[码碼][:：]?\s*([a-zA-Z0-9]{4,6})',
        'open_with_pwd': '{url}?pwd={pwd}'
    }
}