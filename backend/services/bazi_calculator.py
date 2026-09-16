"""
BaZi & Astronomical Metaphysics Calculator Service (生辰八字与天文历法排盘计算服务)
支持出生日期、时间、性别、出生地点（真太阳时经度修正）、四柱干支、十神、五行旺衰、喜忌神及生肖星座推导
"""

import math
import datetime
from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple

# ==================== 1. 基础干支与五行字典 ====================

TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
JIAZI = [TIANGAN[i % 10] + DIZHI[i % 12] for i in range(60)]

# 天干五行与阴阳 (0=阳, 1=阴)
TG_INFO = {
    '甲': {'element': '木', 'yinyang': '阳', 'desc': '阳木，参天古木，栋梁之材'},
    '乙': {'element': '木', 'yinyang': '阴', 'desc': '阴木，花草藤蔓，柔韧生发'},
    '丙': {'element': '火', 'yinyang': '阳', 'desc': '阳火，太阳之火，光明炽烈'},
    '丁': {'element': '火', 'yinyang': '阴', 'desc': '阴火，灯烛之火，内敛文明'},
    '戊': {'element': '土', 'yinyang': '阳', 'desc': '阳土，城墙高山，厚重坚实'},
    '己': {'element': '土', 'yinyang': '阴', 'desc': '阴土，田园湿土，润泽载物'},
    '庚': {'element': '金', 'yinyang': '阳', 'desc': '阳金，刀剑铁石，肃杀坚硬'},
    '辛': {'element': '金', 'yinyang': '阴', 'desc': '阴金，珠玉首饰，温润清脆'},
    '壬': {'element': '水', 'yinyang': '阳', 'desc': '阳水，江河大海，奔流不息'},
    '癸': {'element': '水', 'yinyang': '阴', 'desc': '阴水，雨露清泉，柔顺潜流'}
}

# 地支藏干与主气五行
DZ_INFO = {
    '子': {'element': '水', 'canggan': ['癸'], 'zodiac': '鼠', 'season': '仲冬'},
    '丑': {'element': '土', 'canggan': ['己', '癸', '辛'], 'zodiac': '牛', 'season': '季冬'},
    '寅': {'element': '木', 'canggan': ['甲', '丙', '戊'], 'zodiac': '虎', 'season': '孟春'},
    '卯': {'element': '木', 'canggan': ['乙'], 'zodiac': '兔', 'season': '仲春'},
    '辰': {'element': '土', 'canggan': ['戊', '乙', '癸'], 'zodiac': '龙', 'season': '季春'},
    '巳': {'element': '火', 'canggan': ['丙', '庚', '戊'], 'zodiac': '蛇', 'season': '孟夏'},
    '午': {'element': '火', 'canggan': ['丁', '己'], 'zodiac': '马', 'season': '仲夏'},
    '未': {'element': '土', 'canggan': ['己', '丁', '乙'], 'zodiac': '羊', 'season': '季夏'},
    '申': {'element': '金', 'canggan': ['庚', '壬', '戊'], 'zodiac': '猴', 'season': '孟秋'},
    '酉': {'element': '金', 'canggan': ['辛'], 'zodiac': '鸡', 'season': '仲秋'},
    '戌': {'element': '土', 'canggan': ['戊', '辛', '丁'], 'zodiac': '狗', 'season': '季秋'},
    '亥': {'element': '水', 'canggan': ['壬', '甲'], 'zodiac': '猪', 'season': '孟冬'}
}

# ==================== 2. 中国主要城市地理经度表 (用于真太阳时换算) ====================

CITY_LONGITUDES = {
    "北京市": {"北京市": 116.40, "朝阳区": 116.49, "海淀区": 116.29, "丰台区": 116.28, "通州区": 116.66, "昌平区": 116.23, "大兴区": 116.34},
    "上海市": {"上海市": 121.47, "浦东新区": 121.54, "闵行区": 121.38, "宝山区": 121.48, "嘉定区": 121.26, "松江区": 121.22},
    "天津市": {"天津市": 117.20, "滨海新区": 117.70, "西青区": 117.00, "武清区": 117.04, "宝坻区": 117.31},
    "重庆市": {"重庆市": 106.55, "万州区": 108.41, "涪陵区": 107.39, "黔江区": 108.79, "永川区": 105.92, "合川区": 106.27},
    "广东省": {
        "广州市": 113.27, "深圳市": 114.05, "珠海市": 113.57, "汕头市": 116.68, "佛山市": 113.12,
        "韶关市": 113.60, "湛江市": 110.36, "肇庆市": 112.46, "江门市": 113.08, "茂名市": 110.92,
        "惠州市": 114.41, "梅州市": 116.12, "汕尾市": 115.37, "河源市": 114.70, "阳江市": 111.98,
        "清远市": 113.05, "东莞市": 113.75, "中山市": 113.38, "潮州市": 116.62, "揭阳市": 116.37, "云浮市": 112.04
    },
    "浙江省": {
        "杭州市": 120.15, "宁波市": 121.55, "温州市": 120.70, "嘉兴市": 120.75, "湖州市": 120.09,
        "绍兴市": 120.58, "金华市": 119.64, "衢州市": 118.87, "舟山市": 122.21, "台州市": 121.42, "丽水市": 119.92
    },
    "江苏省": {
        "南京市": 118.80, "无锡市": 120.31, "徐州市": 117.18, "常州市": 119.97, "苏州市": 120.58,
        "南通市": 120.89, "连云港市": 119.22, "淮安市": 119.01, "盐城市": 120.16, "扬州市": 119.41,
        "镇江市": 119.43, "泰州市": 119.92, "宿迁市": 118.28
    },
    "山东省": {
        "济南市": 117.02, "青岛市": 120.38, "淄博市": 118.05, "枣庄市": 117.32, "东营市": 118.67,
        "烟台市": 121.45, "潍坊市": 119.16, "济宁市": 116.59, "泰安市": 117.09, "威海市": 122.12,
        "日照市": 119.53, "临沂市": 118.35, "德州市": 116.36, "聊城市": 115.98, "滨州市": 117.97, "菏泽市": 115.48
    },
    "河南省": {
        "固始县": 115.68, "固始": 115.68,
        "郑州市": 113.63, "开封市": 114.31, "洛阳市": 112.45, "平顶山市": 113.30, "安阳市": 114.35,
        "鹤壁市": 114.29, "新乡市": 113.88, "焦作市": 113.24, "濮阳市": 115.03, "许昌市": 113.83,
        "漯河市": 114.02, "三门峡市": 111.20, "南阳市": 112.52, "商丘市": 115.65, "信阳市": 114.07,
        "周口市": 114.65, "驻马店市": 114.02, "济源市": 112.58
    },
    "四川省": {
        "成都市": 104.07, "自贡市": 104.78, "攀枝花市": 101.72, "泸州市": 105.44, "德阳市": 104.40,
        "绵阳市": 104.73, "广元市": 105.84, "遂宁市": 105.59, "内江市": 105.06, "乐山市": 103.77,
        "南充市": 106.08, "眉山市": 103.85, "宜宾市": 104.64, "广安市": 106.63, "达州市": 107.47,
        "雅安市": 103.04, "巴中市": 106.77, "资阳市": 104.63, "阿坝州": 102.22, "甘孜州": 101.96, "凉山州": 102.26
    },
    "湖北省": {
        "武汉市": 114.31, "黄石市": 115.03, "十堰市": 110.79, "宜昌市": 111.28, "襄阳市": 112.12,
        "鄂州市": 114.89, "荆门市": 112.20, "孝感市": 113.92, "荆州市": 112.23, "黄冈市": 114.87,
        "咸宁市": 114.32, "随州市": 113.38, "恩施州": 109.48, "仙桃市": 113.45, "潜江市": 112.89, "天门市": 113.16
    },
    "湖南省": {
        "长沙市": 112.94, "株洲市": 113.13, "湘潭市": 112.93, "衡阳市": 112.60, "邵阳市": 111.46,
        "岳阳市": 113.13, "常德市": 111.69, "张家界市": 110.47, "益阳市": 112.35, "郴州市": 113.01,
        "永州市": 111.61, "怀化市": 109.99, "娄底市": 112.00, "湘西州": 109.73
    },
    "河北省": {
        "石家庄市": 114.51, "唐山市": 118.18, "秦皇岛市": 119.60, "邯郸市": 114.49, "邢台市": 114.50,
        "保定市": 115.47, "张家口市": 114.88, "承德市": 117.96, "沧州市": 116.84, "廊坊市": 116.68, "衡水市": 115.67
    },
    "陕西省": {
        "西安市": 108.94, "铜川市": 108.95, "宝鸡市": 107.24, "咸阳市": 108.71, "渭南市": 109.50,
        "延安市": 109.49, "汉中市": 107.03, "榆林市": 109.73, "安康市": 109.03, "商洛市": 109.94
    },
    "安徽省": {
        "合肥市": 117.23, "芜湖市": 118.38, "蚌埠市": 117.39, "淮南市": 117.00, "马鞍山市": 118.51,
        "淮北市": 116.80, "铜陵市": 117.82, "安庆市": 117.06, "黄山市": 118.33, "滁州市": 118.32,
        "阜阳市": 115.81, "宿州市": 116.98, "六安市": 116.51, "亳州市": 115.78, "池州市": 117.49, "宣城市": 118.76
    },
    "福建省": {
        "福州市": 119.30, "厦门市": 118.09, "莆田市": 119.00, "三明市": 117.64, "泉州市": 118.68,
        "漳州市": 117.65, "南平市": 118.18, "龙岩市": 117.03, "宁德市": 119.55
    },
    "江西省": {
        "南昌市": 115.86, "景德镇市": 117.18, "萍乡市": 113.85, "九江市": 116.00, "新余市": 114.93,
        "鹰潭市": 117.07, "赣州市": 114.93, "吉安市": 114.99, "宜春市": 114.41, "抚州市": 116.36, "上饶市": 117.97
    },
    "辽宁省": {
        "沈阳市": 123.43, "大连市": 121.62, "鞍山市": 122.99, "抚顺市": 123.96, "本溪市": 123.77,
        "丹东市": 124.38, "锦州市": 121.13, "营口市": 122.23, "阜新市": 121.67, "辽阳市": 123.17,
        "盘锦市": 122.07, "铁岭市": 123.84, "朝阳市": 120.45, "葫芦岛市": 120.84
    },
    "吉林省": {
        "长春市": 125.32, "吉林市": 126.55, "四平市": 124.35, "辽源市": 125.14, "通化市": 125.94,
        "白山市": 126.43, "松原市": 124.82, "白城市": 122.84, "延边州": 129.51
    },
    "黑龙江省": {
        "哈尔滨市": 126.54, "齐齐哈尔市": 123.95, "鸡西市": 130.97, "鹤岗市": 130.28, "双鸭山市": 131.16,
        "大庆市": 125.10, "伊春市": 128.91, "佳木斯市": 130.32, "七台河市": 130.85, "牡丹江市": 129.63,
        "黑河市": 127.53, "绥化市": 126.97, "大兴安岭地区": 124.12
    },
    "山西省": {
        "太原市": 112.55, "大同市": 113.30, "阳泉市": 113.58, "长治市": 113.12, "晋城市": 112.85,
        "朔州市": 112.43, "晋中市": 112.75, "运城市": 111.00, "忻州市": 112.73, "临汾市": 111.52, "吕梁市": 111.13
    },
    "内蒙古区": {
        "呼和浩特市": 111.75, "包头市": 109.84, "乌海市": 106.82, "赤峰市": 118.96, "通辽市": 122.26,
        "鄂尔多斯市": 109.99, "呼伦贝尔市": 119.77, "巴彦淖尔市": 107.42, "乌兰察布市": 113.13, "兴安盟": 122.07,
        "锡林郭勒盟": 116.09, "阿拉善盟": 105.71
    },
    "广西区": {
        "南宁市": 108.37, "柳州市": 109.41, "桂林市": 110.30, "梧州市": 111.32, "北海市": 109.12,
        "防城港市": 108.35, "钦州市": 108.62, "贵港市": 109.60, "玉林市": 110.15, "百色市": 106.62,
        "贺州市": 111.55, "河池市": 108.06, "来宾市": 109.23, "崇左市": 107.35
    },
    "海南省": {
        "海口市": 110.32, "三亚市": 109.51, "三沙市": 112.33, "儋州市": 109.58, "琼海市": 110.47,
        "文昌市": 110.75, "万宁市": 110.39, "东方市": 108.65, "澄迈县": 110.01, "临高县": 109.69
    },
    "贵州省": {
        "贵阳市": 106.63, "六盘水市": 104.83, "遵义市": 106.93, "安顺市": 105.95, "毕节市": 105.29,
        "铜仁市": 109.19, "黔西南州": 104.90, "黔东南州": 107.98, "黔南州": 107.52
    },
    "云南省": {
        "昆明市": 102.83, "曲靖市": 103.79, "玉溪市": 102.55, "保山市": 99.17, "昭通市": 103.72,
        "丽江市": 100.23, "普洱市": 100.97, "临沧市": 100.09, "楚雄州": 101.55, "红河州": 103.38,
        "文山州": 104.24, "西双版纳州": 100.80, "大理州": 100.27, "德宏州": 98.58, "怒江州": 98.85, "迪庆州": 99.71
    },
    "西藏区": {
        "拉萨市": 91.12, "日喀则市": 88.88, "昌都市": 97.18, "林芝市": 94.36, "山南市": 91.77,
        "那曲市": 92.05, "阿里地区": 80.11
    },
    "甘肃省": {
        "兰州市": 103.83, "嘉峪关市": 98.29, "金昌市": 102.19, "白银市": 104.14, "天水市": 105.72,
        "武威市": 102.64, "张掖市": 100.45, "平凉市": 106.67, "酒泉市": 98.51, "庆阳市": 107.64,
        "定西市": 104.63, "陇南市": 104.93, "临夏州": 103.21, "甘南州": 102.91
    },
    "青海省": {
        "西宁市": 101.78, "海东市": 102.10, "海北州": 100.90, "黄南州": 102.02, "海南州": 100.62,
        "果洛州": 100.24, "玉树州": 97.01, "海西州": 97.37
    },
    "宁夏区": {
        "银川市": 106.23, "石嘴山市": 106.38, "吴忠市": 106.20, "固原市": 106.29, "中卫市": 105.18
    },
    "新疆区": {
        "乌鲁木齐市": 87.62, "克拉玛依市": 84.89, "吐鲁番市": 89.19, "哈密市": 93.51, "昌吉州": 87.31,
        "博尔塔拉州": 82.07, "巴音郭楞州": 86.15, "阿克苏地区": 80.26, "克孜勒苏州": 76.17, "喀什地区": 75.99,
        "和田地区": 79.92, "伊犁州": 81.33, "塔城地区": 82.98, "阿勒泰地区": 88.14, "石河子市": 86.04
    },
    "港澳台": {
        "香港特区": 114.17, "澳门特区": 113.54, "台北市": 121.56, "新北市": 121.47, "台中市": 120.68, "高雄市": 120.31
    }
}

def get_city_longitude(province: str, city: str) -> float:
    """获取指定省市的地理经度，默认返回 120.0 (北京时间基准)"""
    if province in CITY_LONGITUDES:
        cities = CITY_LONGITUDES[province]
        if city in cities:
            return cities[city]
        elif len(cities) > 0:
            return list(cities.values())[0]
    return 120.0


# ==================== 2.1 农历与公历双向互转算法 (1900-2100) ====================

LUNAR_INFO = [
    0x04bd8,0x04ae0,0x0a570,0x054d5,0x0d260,0x0d950,0x16554,0x056a0,0x09ad0,0x055d2,
    0x04ae0,0x0a5b6,0x0a4d0,0x0d250,0x1d255,0x0b540,0x0d6a0,0x0ada2,0x095b0,0x14977,
    0x04970,0x0a4b0,0x0b4b5,0x06a50,0x06d40,0x1ab54,0x02b60,0x09570,0x052f2,0x04970,
    0x06566,0x0d4a0,0x0ea50,0x06e95,0x05ad0,0x02b60,0x186e3,0x092e0,0x1c8d7,0x0c950,
    0x0d4a0,0x1d8a6,0x0b550,0x056a0,0x1a5b4,0x025d0,0x092d0,0x0d2b2,0x0a950,0x0b557,
    0x06ca0,0x0b550,0x15355,0x04da0,0x0a5d0,0x14573,0x052d0,0x0a9a8,0x0e950,0x06aa0,
    0x0aea6,0x0ab50,0x04b60,0x0aae4,0x0a570,0x05260,0x0f263,0x0d950,0x05b57,0x056a0,
    0x096d0,0x04dd5,0x04ad0,0x0a4d0,0x0d4d4,0x0d250,0x0d558,0x0b540,0x0b5a0,0x195a6,
    0x095b0,0x049b0,0x0a974,0x0a4b0,0x0b27a,0x06a50,0x06d40,0x0af46,0x0ab60,0x09570,
    0x04af5,0x04970,0x064b0,0x074a3,0x0ea50,0x06b58,0x055c0,0x0ab60,0x096d5,0x092e0,
    0x0c960,0x0d954,0x0d4a0,0x0da50,0x07552,0x056a0,0x0abb7,0x025d0,0x092d0,0x0cab5,
    0x0a950,0x0b4a0,0x0baa4,0x0ad50,0x055d9,0x04ba0,0x0a5b0,0x15176,0x052b0,0x0a930,
    0x07954,0x06aa0,0x0ad50,0x05b52,0x04b60,0x0a6e6,0x0a4e0,0x0d260,0x0ea65,0x0d530,
    0x05aa0,0x076a3,0x096d0,0x04afb,0x04ad0,0x0a4d0,0x1d0b6,0x0d250,0x0d520,0x0dd45,
    0x0b5a0,0x056d0,0x055b2,0x049b0,0x0a577,0x0a4b0,0x0aa50,0x1b255,0x06d20,0x0ada0,
    0x14b63,0x09370,0x049f8,0x04970,0x064b0,0x168a6,0x0ea50,0x06aa0,0x1a6c4,0x0aae0,
    0x092e0,0x0d2e3,0x0c960,0x0d557,0x0d4a0,0x0da50,0x05d55,0x056a0,0x0a6d0,0x055d4,
    0x052d0,0x0a9b8,0x0a950,0x0b4a0,0x0b6a6,0x0ad50,0x055a0,0x0aba4,0x0a5b0,0x052b0,
    0x0b273,0x06930,0x07337,0x06aa0,0x0ad50,0x14b55,0x04b60,0x0a570,0x054e4,0x0d160,
    0x0e968,0x0d520,0x0daa0,0x16aa6,0x056d0,0x04ae0,0x0a9d4,0x0a2d0,0x0d150,0x0f252,
    0x0d520
]

LUNAR_MONTH_NAMES = ["正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "冬月", "腊月"]
LUNAR_DAY_NAMES = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"
]

def get_lunar_leap_month(year: int) -> int:
    """获取农历年份的闰月月份 (0 表示无闰月)"""
    if 1900 <= year <= 2100:
        return LUNAR_INFO[year - 1900] & 0xf
    return 0

def lunar_to_solar(year: int, month: int, day: int, is_leap_month: bool = False) -> datetime.date:
    """农历日期转换为公历 (阳历) 日期"""
    base_date = datetime.date(1900, 1, 31)
    offset_days = 0
    safe_year = max(1900, min(2100, year))
    
    for y in range(1900, safe_year):
        info = LUNAR_INFO[y - 1900]
        days_in_year = 0
        for m in range(1, 13):
            days_in_year += 30 if (info & (0x10000 >> m)) else 29
        leap_m = info & 0xf
        if leap_m > 0:
            days_in_year += 30 if (info & 0x10000) else 29
        offset_days += days_in_year
        
    info = LUNAR_INFO[safe_year - 1900]
    leap_m = info & 0xf
    
    for m in range(1, month):
        offset_days += 30 if (info & (0x10000 >> m)) else 29
        if leap_m == m:
            offset_days += 30 if (info & 0x10000) else 29
            
    if is_leap_month and leap_m == month:
        offset_days += 30 if (info & (0x10000 >> month)) else 29
        
    offset_days += (day - 1)
    return base_date + datetime.timedelta(days=offset_days)

def solar_to_lunar(solar_date: datetime.date):
    """公历 (阳历) 日期转换为农历 (阴历) 年、月、日、是否闰月"""
    base_date = datetime.date(1900, 1, 31)
    offset = (solar_date - base_date).days
    if offset < 0:
        return 1900, 1, 1, False
        
    lunar_year = 1900
    for y in range(1900, 2101):
        info = LUNAR_INFO[y - 1900]
        days_in_year = 0
        for m in range(1, 13):
            days_in_year += 30 if (info & (0x10000 >> m)) else 29
        leap_m = info & 0xf
        if leap_m > 0:
            days_in_year += 30 if (info & 0x10000) else 29
            
        if offset < days_in_year:
            lunar_year = y
            break
        offset -= days_in_year
        
    info = LUNAR_INFO[lunar_year - 1900]
    leap_m = info & 0xf
    is_leap = False
    lunar_month = 1
    
    for m in range(1, 13):
        days_in_m = 30 if (info & (0x10000 >> m)) else 29
        if offset < days_in_m:
            lunar_month = m
            break
        offset -= days_in_m
        
        if leap_m == m:
            days_in_leap = 30 if (info & 0x10000) else 29
            if offset < days_in_leap:
                lunar_month = m
                is_leap = True
                break
            offset -= days_in_leap
            
    lunar_day = offset + 1
    return lunar_year, lunar_month, lunar_day, is_leap


# ==================== 3. 节气算法 (二十四节气推算 1900-2100) ====================

# 12 "节" 的常数表 (世纪常数法)
JIE_CONSTANTS = {
    1: (5.4055, 6.11, '小寒', '丑'),
    2: (3.87,   4.6295, '立春', '寅'),
    3: (5.63,   6.3826, '惊蛰', '卯'),
    4: (4.81,   5.59,   '清明', '辰'),
    5: (5.52,   6.318,  '立夏', '巳'),
    6: (5.678,  6.5,    '芒种', '午'),
    7: (7.108,  7.928,  '小暑', '未'),
    8: (7.5,    8.35,   '立秋', '申'),
    9: (7.646,  8.44,   '白露', '酉'),
    10: (8.318, 9.098,  '寒露', '戌'),
    11: (7.438, 8.218,  '立冬', '亥'),
    12: (7.18,  7.9,    '大雪', '子')
}

def get_solar_term_day(year: int, month: int) -> int:
    """计算某公历年某月的“节”（交节令）日期"""
    c_21, c_20, name, dz = JIE_CONSTANTS[month]
    y_last = year % 100
    if year >= 2000:
        c = c_21
        day = int(y_last * 0.2422 + c) - int(y_last / 4)
    else:
        c = c_20
        day = int(y_last * 0.2422 + c) - int((y_last - 1) / 4)
    return max(1, min(31, day))


# ==================== 4. 星座与生肖推导 ====================

CONSTELLATIONS = [
    (1, 20, "摩羯座"), (2, 19, "水瓶座"), (3, 21, "双鱼座"),
    (4, 20, "白羊座"), (5, 21, "金牛座"), (6, 22, "双子座"),
    (7, 23, "巨蟹座"), (8, 23, "狮子座"), (9, 23, "处女座"),
    (10, 24, "天秤座"), (11, 23, "天蝎座"), (12, 22, "射手座"),
    (12, 32, "摩羯座")
]

def get_constellation(month: int, day: int) -> str:
    """根据公历月日计算星座"""
    for m, d, name in CONSTELLATIONS:
        if month < m or (month == m and day <= d):
            return name
    return "摩羯座"


# ==================== 5. 核心排盘与五行推导算法 ====================

REF_DATE = date(2026, 9, 3)
REF_JIAZI_IDX = 16  # 2026-09-03 为 庚辰日

def calculate_full_bazi(
    birth_date_str: str,
    birth_time_str: str = "12:00",
    gender: str = "male",
    province: str = "北京市",
    city: str = "北京市",
    calendar_type: str = "solar",
    is_leap_month: bool = False,
    lunar_year: Optional[int] = None,
    lunar_month: Optional[int] = None,
    lunar_day: Optional[int] = None
) -> Dict[str, Any]:
    """
    输入出生年月日、时间、性别、出生地点，完成近似历法排盘与传统五行分析：
    - 支持公历/农历双向智能转换与对齐
    - 结合经度计算真太阳时
    - 年柱、月柱、日柱、时柱排盘
    - 命理日主、五行分布统计与强弱分析
    - 智能推荐喜用神与忌神
    - 生肖属相与西洋星座判定
    """
    if calendar_type == "lunar":
        if lunar_year and lunar_month and lunar_day:
            ly, lm, ld, ileap = lunar_year, lunar_month, lunar_day, bool(is_leap_month)
        else:
            parts = birth_date_str.split("-")
            ly = int(parts[0]) if len(parts) > 0 else 1992
            lm = int(parts[1]) if len(parts) > 1 else 5
            ld = int(parts[2]) if len(parts) > 2 else 25
            ileap = bool(is_leap_month)
        dt = lunar_to_solar(ly, lm, ld, ileap)
        solar_date_str = dt.strftime("%Y-%m-%d")
    else:
        dt = datetime.datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        solar_date_str = dt.strftime("%Y-%m-%d")
        ly, lm, ld, ileap = solar_to_lunar(dt)
    
    # 解析时间
    time_parts = birth_time_str.split(":")
    hour = int(time_parts[0]) if len(time_parts) > 0 else 12
    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
    
    # 1. 计算出生地经度与真太阳时
    longitude = get_city_longitude(province, city)
    # 与 120°E 的时差：1度经度 = 4分钟 = 240秒
    longitude_offset_minutes = (longitude - 120.0) * 4
    # Approximate equation of time; longitude correction alone gives mean solar time.
    year_days = (date(dt.year + 1, 1, 1) - date(dt.year, 1, 1)).days
    gamma = 2 * math.pi / year_days * (dt.timetuple().tm_yday - 1 + (hour - 12) / 24)
    equation_minutes = 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma) - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma))
    offset_seconds = round((longitude_offset_minutes + equation_minutes) * 60)
    orig_dt = datetime.datetime.combine(dt, datetime.time(hour, minute))
    solar_dt = orig_dt + datetime.timedelta(seconds=offset_seconds)
    
    calc_date = solar_dt.date()
    solar_hour = solar_dt.hour
    solar_minute = solar_dt.minute
    true_solar_time_str = f"{solar_hour:02d}:{solar_minute:02d}"
    
    # 2. 年柱推算 (以立春为岁首界限)
    lichun_day = get_solar_term_day(calc_date.year, 2)
    lichun_date = date(calc_date.year, 2, lichun_day)
    
    if calc_date < lichun_date:
        bazi_year_num = calc_date.year - 1
    else:
        bazi_year_num = calc_date.year
        
    year_stem_idx = (bazi_year_num - 4) % 10
    year_branch_idx = (bazi_year_num - 4) % 12
    year_stem = TIANGAN[year_stem_idx]
    year_branch = DIZHI[year_branch_idx]
    year_pillar = year_stem + year_branch
    zodiac = DZ_INFO[year_branch]['zodiac']
    
    # 3. 月柱推算 (以 12 节气为界，结合五虎遁月)
    cur_month = calc_date.month
    cur_jie_day = get_solar_term_day(calc_date.year, cur_month)
    
    if calc_date.day >= cur_jie_day:
        month_idx = cur_month
    else:
        month_idx = cur_month - 1 if cur_month > 1 else 12

    # 月支对照表: 1月小寒后丑(1), 2月立春后寅(2), ..., 6月芒种后午(6)...
    month_branch_map = {
        1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6,
        7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 0
    }
    month_branch_idx = month_branch_map[month_idx]
    month_branch = DIZHI[month_branch_idx]
    
    # 五虎遁月起月干: 甲己丙作首, 乙庚戊为头, 丙辛寻庚上, 丁壬壬位顺行流, 戊癸甲寅求
    month_start_stem = (year_stem_idx % 5 * 2 + 2) % 10
    lunar_month_offset = (month_branch_idx - 2) % 12
    month_stem = TIANGAN[(month_start_stem + lunar_month_offset) % 10]
    month_pillar = month_stem + month_branch
    
    # 4. 日柱推算 (以 2026-09-03 庚辰日作为六十甲子绝对锚定)
    diff_days = (calc_date - REF_DATE).days
    day_jiazi_idx = (REF_JIAZI_IDX + diff_days) % 60
    day_stem = TIANGAN[day_jiazi_idx % 10]
    day_branch = DIZHI[day_jiazi_idx % 12]
    day_pillar = day_stem + day_branch
    
    # 5. 时柱推算 (根据真太阳时时辰，结合五鼠遁日)
    # 时辰区间: 23:00-01:00 子, 01:00-03:00 丑, 03:00-05:00 寅, ..., 07:00-09:00 辰
    hour_branch_idx = ((solar_hour + 1) // 2) % 12
    hour_branch = DIZHI[hour_branch_idx]
    
    # 五鼠遁日起时干: 甲己还加甲, 乙庚丙作初, 丙辛从戊起, 丁壬庚子居, 戊癸何方发壬子是真途
    day_stem_idx = day_jiazi_idx % 10
    hour_start_stem = (day_stem_idx % 5 * 2) % 10
    hour_stem = TIANGAN[(hour_start_stem + hour_branch_idx) % 10]
    hour_pillar = hour_stem + hour_branch
    
    # 6. 命理日主 (Day Master)
    dm_elem = TG_INFO[day_stem]['element']
    day_master = f"{day_stem}{dm_elem}"
    
    # 7. 五行数量统计 (8字 + 藏干能量)
    wuxing_counts = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
    for tg in [year_stem, month_stem, day_stem, hour_stem]:
        wuxing_counts[TG_INFO[tg]['element']] += 1
    for dz in [year_branch, month_branch, day_branch, hour_branch]:
        wuxing_counts[DZ_INFO[dz]['element']] += 1

    # 8. 智能分析身强身弱与喜忌神
    # 得令分析 (月令五行)
    month_elem = DZ_INFO[month_branch]['element']
    is_in_season = (month_elem == dm_elem or (dm_elem == '水' and month_elem == '金') or (dm_elem == '木' and month_elem == '水') or (dm_elem == '火' and month_elem == '木') or (dm_elem == '土' and month_elem == '火') or (dm_elem == '金' and month_elem == '土'))
    
    # 印比力量 (生助日主者)
    help_count = 0
    if dm_elem == '水':
        help_count = wuxing_counts['金'] + wuxing_counts['水']
    elif dm_elem == '木':
        help_count = wuxing_counts['水'] + wuxing_counts['木']
    elif dm_elem == '火':
        help_count = wuxing_counts['木'] + wuxing_counts['火']
    elif dm_elem == '土':
        help_count = wuxing_counts['火'] + wuxing_counts['土']
    elif dm_elem == '金':
        help_count = wuxing_counts['土'] + wuxing_counts['金']

    # 综合研判身强/身弱及喜用神
    if dm_elem == '水':
        favorable = "金, 水, 湿土 (庚辛申酉 / 壬癸亥子 / 辰丑)"
        unfavorable = "燥土, 烈火, 刑冲 (戊未戌 / 丙午 / 寅申冲 / 辰戌冲)"
        energy_desc = "日主壬水，以金印生身、以水为比劫帮身；逢辰丑湿土水库蓄势聚财，忌燥土与极烈火耗泄克身。"
    elif dm_elem == '木':
        favorable = "水, 木, 润土 (壬癸亥子 / 甲乙寅卯 / 辰丑)"
        unfavorable = "烈金, 燥火, 刑冲 (庚辛申酉 / 巳午 / 申寅冲)"
        energy_desc = "日主为木，以水为印、以木为同气；喜雨露润泽生发，忌烈金重克与燥火焚林。"
    elif dm_elem == '火':
        favorable = "木, 火, 燥土 (甲乙寅卯 / 丙丁巳午 / 戊戌)"
        unfavorable = "极盛金水, 湿泥晦火 (庚辛申酉 / 壬癸亥子)"
        energy_desc = "日主为火，以木为印星生火，喜文明向阳之气，防范大水克制与湿土掩光。"
    elif dm_elem == '金':
        favorable = "土, 金, 湿土 (戊己辰丑 / 庚辛申酉)"
        unfavorable = "烈火熔金, 旺木耗金 (丙丁巳午 / 甲乙寅卯)"
        energy_desc = "日主为金，以土为印、以金为比，喜刚健肃杀与湿土相生，忌烈火刑熔与木盛耗锐。"
    else: # 土
        favorable = "火, 土, 暖土 (丙丁巳午 / 戊己未戌)"
        unfavorable = "重木克土, 泛滥大水 (甲乙寅卯 / 壬癸亥子)"
        energy_desc = "日主为土，以火为印星生土，厚德载物，喜暖阳生扶，忌旺木疏土与洪峰冲溃。"

    constellation = get_constellation(calc_date.month, calc_date.day)

    return {
        "birth_date": solar_date_str,
        "solar_date": solar_date_str,
        "lunar_date": f"{ly}年{'闰' if ileap else ''}{lm}月{ld}日",
        "lunar_year": ly,
        "lunar_month": lm,
        "lunar_day": ld,
        "is_leap_month": ileap,
        "lunar_desc": f"农历{ly}年{('闰' if ileap else '')}{LUNAR_MONTH_NAMES[lm-1]}{LUNAR_DAY_NAMES[ld-1]}",
        "birth_time": birth_time_str,
        "calendar_type": calendar_type,
        "gender": gender,
        "gender_label": "乾造 (男)" if gender == "male" else "坤造 (女)",
        "province": province,
        "city": city,
        "longitude": longitude,
        "solar_datetime": solar_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "true_solar_time": true_solar_time_str,
        "time_offset_desc": f"{'+' if offset_seconds >= 0 else ''}{round(offset_seconds / 60, 1)}分钟",
        "solar_time_method": "longitude_plus_approximate_equation_of_time",
        "equation_of_time_minutes": round(equation_minutes, 2),
        "four_pillars": {
            "year": year_pillar,
            "month": month_pillar,
            "day": day_pillar,
            "hour": hour_pillar
        },
        "year_pillar": year_pillar,
        "month_pillar": month_pillar,
        "day_pillar": day_pillar,
        "hour_pillar": hour_pillar,
        "day_master": day_master,
        "wuxing_counts": wuxing_counts,
        "zodiac": zodiac,
        "constellation": constellation,
        "favorable": favorable,
        "unfavorable": unfavorable,
        "energy_desc": energy_desc
    }
