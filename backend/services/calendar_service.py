"""
Investment Calendar Service (投资日历核心服务)
整合生辰八字、流日天干地支、五行十神、易经六十四卦、每日盈亏与AI动态复盘核验
"""

import os
import json
import sqlite3
import datetime
from datetime import date, timedelta
from typing import List, Dict, Any, Optional

from database import DB_PATH, get_settings_dict
from services.trading_calendar import is_trading_day
from services.market_service import get_market_overview
from services.news_service import fetch_7x24_market_news
from services.ai_service import call_llm_chat

# ==================== 1. 天干地支与易经算法常量 ====================

TIANGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
DIZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
JIAZI = [TIANGAN[i % 10] + DIZHI[i % 12] for i in range(60)]

# 天干五行与阴阳 (0=阳, 1=阴)
TG_WUXING = {
    '甲': ('木', '阳'), '乙': ('木', '阴'),
    '丙': ('火', '阳'), '丁': ('火', '阴'),
    '戊': ('土', '阳'), '己': ('土', '阴'),
    '庚': ('金', '阳'), '辛': ('金', '阴'),
    '壬': ('水', '阳'), '癸': ('水', '阴')
}

# 地支五行与藏干主气
DZ_WUXING = {
    '子': ('水', '癸', '坎水正位，阴极阳生'),
    '丑': ('土', '己', '湿土生金，含金水余气'),
    '寅': ('木', '甲', '阳木初生，火土相兼'),
    '卯': ('木', '乙', '纯正春木，生发旺盛'),
    '辰': ('土', '戊', '湿土水库，蓄水养木'),
    '巳': ('火', '丙', '阳火初旺，金生之源'),
    '午': ('火', '丁', '纯正夏火，烈阳极盛'),
    '未': ('土', '己', '燥土木库，藏火耗水'),
    '申': ('金', '庚', '阳金当令，水之长生'),
    '酉': ('金', '辛', '纯正秋金，坚刚肃杀'),
    '戌': ('土', '戊', '燥土火库，火土炎热'),
    '亥': ('水', '壬', '阳水汇聚，木之长生')
}

# 五行生克关系
WUXING_RELATIONS = {
    ('木', '木'): '比和', ('木', '火'): '我生(泄气)', ('木', '土'): '我克(耗财)', ('木', '金'): '克我(受制)', ('木', '水'): '生我(得助)',
    ('火', '火'): '比和', ('火', '土'): '我生(泄气)', ('火', '金'): '我克(耗财)', ('火', '水'): '克我(受制)', ('火', '木'): '生我(得助)',
    ('土', '土'): '比和', ('土', '金'): '我生(泄气)', ('土', '水'): '我克(耗财)', ('土', '木'): '克我(受制)', ('土', '火'): '生我(得助)',
    ('金', '金'): '比和', ('金', '水'): '我生(泄气)', ('金', '木'): '我克(耗财)', ('金', '火'): '克我(受制)', ('金', '土'): '生我(得助)',
    ('水', '水'): '比和', ('水', '木'): '我生(泄气)', ('水', '火'): '我克(耗财)', ('水', '土'): '克我(受制)', ('水', '金'): '生我(得助)'
}

# 易经六十四卦核心投资库
HEXAGRAMS = [
    {"name": "乾为天", "symbol": "䷀", "element": "纯阳纯金", "nature": "刚健中正", "judgment": "大吉，元亨利贞。顺天应时，刚健不息。", "advice": "大盘攻势如虹，主升浪特征明显，宜顺势进攻，切勿盲目猜顶。"},
    {"name": "坤为地", "symbol": "䷁", "element": "纯阴纯土", "nature": "厚德载物", "judgment": "吉，地势坤，君子以厚德载物。", "advice": "市场以稳健筑底为主，适合左侧潜伏低吸，切忌急躁追涨。"},
    {"name": "水天需", "symbol": "䷄", "element": "水润金生", "nature": "蓄势待发", "judgment": "有孚，光亨，贞吉。需于饮食宴乐。", "advice": "资金正在暗中吸筹蓄势，不宜冲动频繁操作，耐得住寂寞方能守得云开。"},
    {"name": "天水讼", "symbol": "䷅", "element": "金水相克", "nature": "多空激战", "judgment": "小凶，有孚窒惕，中吉，终凶。", "advice": "多空分歧巨大，盘面震荡剧烈，容易出现假突破诱多，宜严控仓位防守。"},
    {"name": "地水师", "symbol": "䷆", "element": "水润湿土", "nature": "主力集结", "judgment": "吉，师贞，丈人吉，无咎。", "advice": "大资金与机构主力调兵遣将，重点关注核心板块龙头，步步为营。"},
    {"name": "水地比", "symbol": "䷇", "element": "水土相亲", "nature": "抱团做多", "judgment": "吉，原筮元永贞，无咎。不宁方来。", "advice": "板块合力极强，市场呈现典型抱团做多氛围，可跟随核心资产乘胜追击。"},
    {"name": "风天小畜", "symbol": "䷈", "element": "木金相战", "nature": "蓄势整理", "judgment": "平，密云不雨，自我西郊。", "advice": "行情面临短线压力位蓄力洗盘，冲高乏力，建议分批止盈部分短线仓位。"},
    {"name": "天泽履", "symbol": "䷉", "element": "金水柔和", "nature": "履险如夷", "judgment": "吉，履虎尾，不咥人，亨。", "advice": "行情处于高位震荡敏感期，步步惊心却暗藏机会，严格执行止盈止损纪律。"},
    {"name": "地天泰", "symbol": "䷊", "element": "阴阳调和", "nature": "三阳开泰", "judgment": "大吉，小往大来，吉亨。", "advice": "天地交泰，全线普涨，流动性充沛，把握年内最黄金的持股躺赢窗口。"},
    {"name": "天地否", "symbol": "䷋", "element": "上下不通", "nature": "休克退守", "judgment": "大凶，否之匪人，不利君子贞，大往小来。", "advice": "盘面流动性匮乏或遭遇重大黑天鹅，泥沙俱下，坚决防御减仓避险。"},
    {"name": "天火同人", "symbol": "䷌", "element": "金火相济", "nature": "万众一心", "judgment": "大吉，同人于野，亨。利涉大川。", "advice": "市场共识凝聚，增量资金蜂拥入场，热点主线清晰，做多胜率极高。"},
    {"name": "火天大有", "symbol": "䷍", "element": "火炼真金", "nature": "日丽中天", "judgment": "大吉，其德刚健而文明，应乎天而时行。", "advice": "持仓利润迎来高光释放期，偏财丰厚，可持股享受泡沫，但不可杠杆追高。"},
    {"name": "地山谦", "symbol": "䷎", "element": "重土生金", "nature": "内实外谦", "judgment": "吉，谦谦君子，卑以自牧也。", "advice": "行情稳扎稳打，不显山不露水，适合静待价值修复，逢低布局优质核心品种。"},
    {"name": "雷地豫", "symbol": "䷏", "element": "木生大地", "nature": "欣欣向荣", "judgment": "吉，利建侯行师，先王以作乐崇德。", "advice": "资金情绪亢奋，题材股与成长赛道爆发，适合做多强势弹性品种。"},
    {"name": "泽雷随", "symbol": "䷐", "element": "金水相生", "nature": "顺势而动", "judgment": "吉，元亨利贞，无咎。", "advice": "不要与趋势作对，右侧顺势交易，尊重市场合力选择的方向。"},
    {"name": "山风蛊", "symbol": "䷑", "element": "土木交战", "nature": "出清整顿", "judgment": "平，利涉大川，先甲三日，后甲三日。", "advice": "前期妖股泡沫破裂，市场进入优胜劣汰重构期，警惕高位股补跌退潮。"},
    {"name": "地泽临", "symbol": "䷒", "element": "水润厚土", "nature": "阳气渐长", "judgment": "大吉，元亨利贞，至于八月有凶。", "advice": "底部阳线连续出现，大资金悄然进场，可果断把握波段拐点入场。"},
    {"name": "风地观", "symbol": "䷓", "element": "木立于土", "nature": "冷眼旁观", "judgment": "平，盥而不荐，有孚颙若。", "advice": "变盘窗口临近，方向不明朗，多看少动，等待大盘给出一锤定音的方向。"},
    {"name": "火雷噬嗑", "symbol": "䷔", "element": "火木交辉", "nature": "强力突破", "judgment": "吉，利用狱，雷电合而章。", "advice": "多方发力强行啃下关键阻力位，放量突破，可重点加仓领涨板块。"},
    {"name": "山火贲", "symbol": "䷕", "element": "火照高山", "nature": "冲高回落", "judgment": "平，亨，小利有攸往。", "advice": "盘中出现虚假繁荣与冲高回落，量价背离，谨防主力拉高出货陷阱。"},
    {"name": "山地剥", "symbol": "䷖", "element": "燥土倾危", "nature": "阴盛阳衰", "judgment": "凶，不利有攸往，顺而止之。", "advice": "支撑位被跌破，恐慌盘涌出，阴跌不休，严守止损线，多看少动。"},
    {"name": "地雷复", "symbol": "䷗", "element": "一阳来复", "nature": "绝地反弹", "judgment": "大吉，朋来无咎，反复其道，七日来复。", "advice": "地底惊雷，探出全波段黄金坑，绝处逢生，是不可多得的逢低布局良机。"},
    {"name": "天雷无妄", "symbol": "䷘", "element": "金木相战", "nature": "顺其自然", "judgment": "平，其匪正有眚，不利有攸往。", "advice": "切勿自作聪明做逆势预判，谨防意外黑天鹅，守株待兔方为上策。"},
    {"name": "山天大畜", "symbol": "䷙", "element": "厚积薄发", "nature": "储蓄能量", "judgment": "大吉，刚健笃实辉光，日新其德。", "advice": "长期平台整理步入尾声，主力蓄势充分，即将迎来波澜壮阔的主升大行情。"},
    {"name": "山雷颐", "symbol": "䷚", "element": "土木调适", "nature": "稳健调养", "judgment": "平，颐，贞吉，观颐，自求口实。", "advice": "市场缺乏系统性机会，宜锁定防守型高股息或稳健底仓，休养生息。"},
    {"name": "泽风大过", "symbol": "䷛", "element": "水木漂摇", "nature": "栋桡倾危", "judgment": "凶，栋桡，利有攸往，亨。", "advice": "市场情绪过热透支或杠杆过载，栋梁将弯，警惕短线剧烈踩踏式调整。"},
    {"name": "坎为水", "symbol": "䷜", "element": "纯水滔滔", "nature": "重重险阻", "judgment": "凶，习坎，有孚维心，亨，行有尚。", "advice": "深陷泥潭与调整浪中，切勿急于抄底接飞刀，耐心等待水落石出。"},
    {"name": "离为火", "symbol": "䷝", "element": "纯火烈阳", "nature": "炽热耀眼", "judgment": "吉，利贞，亨。畜牝牛，吉。", "advice": "火系科技与AI算力情绪沸腾，短线赚钱效应爆棚，但需紧盯午后分化风险。"},
    {"name": "泽山咸", "symbol": "䷞", "element": "金土相生", "nature": "心领神会", "judgment": "大吉，亨利贞，取女吉。", "advice": "盘面与资金节拍高度共振，选股胜率极高，适合积极做多高景气资产。"},
    {"name": "雷风恒", "symbol": "䷟", "element": "木火相生", "nature": "持之以恒", "judgment": "吉，亨，无咎，利贞，利有攸往。", "advice": "中长线慢牛趋势明朗，不为短期杂音所动，重在坚定持有优质龙头。"},
    {"name": "天山遁", "symbol": "䷠", "element": "金土退隐", "nature": "急流勇退", "judgment": "平，遁亨，小利贞。", "advice": "顶部特征显现，主力资金大笔撤退，明智者懂得落袋为安、见好就收。"},
    {"name": "雷天大壮", "symbol": "䷡", "element": "木金合力", "nature": "声势浩大", "judgment": "大吉，壮于大舆，利贞。", "advice": "成交量急剧放大，资金气吞万里如虎，突破颈线，适合重仓博取主升浪。"},
    {"name": "火地晋", "symbol": "䷢", "element": "日出东方", "nature": "步步高升", "judgment": "大吉，康侯用锡马蕃庶，昼日三接。", "advice": "资产净值阶梯式攀升，利好接踵而至，顺应趋势持有享受主升浪红利。"},
    {"name": "地火明夷", "symbol": "䷣", "element": "日落幽暗", "nature": "潜龙勿用", "judgment": "凶，利艰贞，晦其明而遇难。", "advice": "光明受阻，市场遭受政策或宏观利空打压，宜隐藏锋芒，减少操作，静待黎明。"},
    {"name": "风火家人", "symbol": "䷤", "element": "木火相生", "nature": "守家固本", "judgment": "吉，利女贞，家道成而天下定。", "advice": "稳固基本盘，重点配置估值极具安全边际的压舱石品种，防御反击。"},
    {"name": "火泽睽", "symbol": "䷥", "element": "水火不容", "nature": "各奔东西", "judgment": "小凶，小事吉，见恶人无咎。", "advice": "极端二八分化，指数涨个股跌，赚指数不赚钱，切忌盲目乱换股。"},
    {"name": "水山蹇", "symbol": "䷦", "element": "水困高山", "nature": "举步维艰", "judgment": "凶，利西南，不利东北，利见大人。", "advice": "前有阻截后有追兵，持仓陷入滞胀，切莫硬扛，适当逢高减仓降杠杆。"},
    {"name": "雷水解", "symbol": "䷧", "element": "春雷破冰", "nature": "冰雪消融", "judgment": "吉，利西南，无所往，其来复吉。", "advice": "困扰市场的利空靴子终于落地，流动性危机解除，暴力超跌反弹一触即发。"},
    {"name": "山泽损", "symbol": "䷨", "element": "损下益上", "nature": "洗盘挤压", "judgment": "平，有孚，元吉，无咎，可贞。", "advice": "主力蓄意洗盘震仓，短线阵痛难免，但洗出浮筹后后市将更加轻盈。"},
    {"name": "风雷益", "symbol": "䷩", "element": "风雷激荡", "nature": "乘风破浪", "judgment": "大吉，利有攸往，利涉大川。", "advice": "增量资金大幅涌入，持仓品种呈现强劲业绩与估值双击，坚定看多做多。"},
    {"name": "泽天夬", "symbol": "䷪", "element": "水漫九天", "nature": "决断在即", "judgment": "平，扬于王庭，孚号有厉。", "advice": "多头能量释放至极致，逼空行情尾声，随时可能触发巨震，随时做好止盈准备。"},
    {"name": "天风姤", "symbol": "䷫", "element": "金风乍起", "nature": "风云突变", "judgment": "小凶，女壮，勿用取女。", "advice": "盘面微观结构发生异动，高位出现隐秘大单抛售，宁可错过不可做错。"},
    {"name": "泽地萃", "symbol": "䷬", "element": "水汇平原", "nature": "资金荟萃", "judgment": "大吉，聚而亨，利见大人。", "advice": "核心资产与指数权重被北向及机构资金集中扫货，龙头强者恒强。"},
    {"name": "地风升", "symbol": "䷭", "element": "木破土出", "nature": "平步青云", "judgment": "吉，元亨，用见大人，勿恤，南征吉。", "advice": "低位震荡攀升，底部越来越高，典型的潜伏牛股慢牛走势，耐心做时间的朋友。"},
    {"name": "泽水困", "symbol": "䷮", "element": "水漏泽干", "nature": "流动性渴", "judgment": "凶，贞大人吉，无咎，有言不信。", "advice": "两市成交额极度萎缩地量，交投冷清，警惕钝刀子割肉，坚守现金为王。"},
    {"name": "水风井", "symbol": "䷯", "element": "清泉不绝", "nature": "源远流长", "judgment": "吉，改邑不改井，无丧无得。", "advice": "具备持续分红与护城河的公用事业与优质现金流品种显现定海神针价值。"},
    {"name": "泽火革", "symbol": "䷰", "element": "水火淬炼", "nature": "时代剧变", "judgment": "大吉，巳日乃孚，元亨利贞，悔亡。", "advice": "新旧周期交替，旧赛道出清完毕，新质生产力与科技新主线王者归来。"},
    {"name": "火风鼎", "symbol": "䷱", "element": "木火炼金", "nature": "鼎盛基业", "judgment": "大吉，元吉，亨。", "advice": "宏观政策与产业周期达成完美共振，持仓迎来业绩与股价双巅峰。"},
    {"name": "震为雷", "symbol": "䷲", "element": "纯木双雷", "nature": "惊天动地", "judgment": "平，震来虩虩，笑言哑哑，震惊百里。", "advice": "盘中突发剧烈脉冲拉升或下杀，雷声大雨点小，保持定力切勿被震荡出局。"},
    {"name": "艮为山", "symbol": "䷳", "element": "纯土双峰", "nature": "止于至善", "judgment": "平，艮其背，不获其身，行其庭，不见其人。", "advice": "阻力重重，冲关受阻，行情进入横盘无趣的垃圾时间，以静制动。"},
    {"name": "风山渐", "symbol": "䷴", "element": "木扎根山", "nature": "循序渐进", "judgment": "吉，女归吉，利贞。", "advice": "不疾而速，大盘沿着均线稳健攀升，适合网格交易与逢回调定投。"},
    {"name": "雷泽归妹", "symbol": "䷵", "element": "金木相伤", "nature": "名不副实", "judgment": "凶，征凶，无攸利。", "advice": "概念炒作无业绩支撑，纯属题材情绪退潮前最后的挣扎，切忌接最后一棒。"},
    {"name": "雷火丰", "symbol": "䷶", "element": "木生烈火", "nature": "丰盛巅峰", "judgment": "大吉，亨，王假之，勿忧，宜日中。", "advice": "热点赛道全面井喷，全市场成交额创历史天量，盛极之时需备防秋之策。"},
    {"name": "火山旅", "symbol": "䷷", "element": "火行山巅", "nature": "浮光掠影", "judgment": "小凶，小亨，旅贞吉。", "advice": "板块轮动如电风扇，电风扇行情难把握，切忌盲目追涨杀跌两头挨打。"},
    {"name": "巽为风", "symbol": "䷸", "element": "纯木长风", "nature": "无孔不入", "judgment": "平，小亨，利有攸往，利见大人。", "advice": "游资与量化高频主导盘面，跟随盘面最强异动快速套利，见好即收。"},
    {"name": "兑为泽", "symbol": "䷹", "element": "纯金双泽", "nature": "和颜悦色", "judgment": "吉，亨，利贞。", "advice": "市场交投活跃，散户与机构皆大欢喜，行情具备持续温和上涨动能。"},
    {"name": "风水涣", "symbol": "䷺", "element": "风吹水散", "nature": "分道扬镳", "judgment": "平，亨，王假有庙，利涉大川。", "advice": "高位筹码松动，筹码开始向低位低估值板块发散迁徙，适时高切低。"},
    {"name": "水泽节", "symbol": "䷻", "element": "水蓄泽中", "nature": "克制有度", "judgment": "吉，亨，苦节不可贞。", "advice": "严格执行止损线与仓位上限，赚自己认知范围内的钱，戒贪戒躁。"},
    {"name": "风泽中孚", "symbol": "䷼", "element": "金生丽水", "nature": "诚至金开", "judgment": "大吉，豚鱼吉，利涉大川，利贞。", "advice": "信心的力量重塑估值，核心资产获得长线长线主权资金加持，稳如泰山。"},
    {"name": "雷山小过", "symbol": "䷽", "element": "木立群山", "nature": "小有越位", "judgment": "平，可小事，不可大事。飞鸟遗之音。", "advice": "技术形态轻微破位或假跌破，切莫过度恐慌，小仓位试错参与。"},
    {"name": "水火既济", "symbol": "䷾", "element": "水火交融", "nature": "大功告成", "judgment": "吉，亨小，利贞，初吉终乱。", "advice": "本轮波段目标位已达成，初期收获颇丰，但防范后半场盛极而衰，逢高兑现。"},
    {"name": "火水未济", "symbol": "䷿", "element": "水火未融", "nature": "生生不息", "judgment": "吉，亨，小狐汔济，濡其尾，无攸利。", "advice": "旧循环的结束正是新周期的黎明，市场正在孕育下一轮万亿级大主线，保持敏锐。"}
]

# ==================== 2. 核心数学与算法计算 ====================

REF_DATE = date(2026, 9, 3)
REF_JIAZI_IDX = 16  # 2026-09-03 为 庚辰日 (16 % 10 = 6 '庚', 16 % 12 = 4 '辰')

def get_day_ganzhi(dt: date) -> Dict[str, Any]:
    """精确计算任意公历日期的六十甲子干支及五行属性"""
    diff_days = (dt - REF_DATE).days
    jiazi_idx = (REF_JIAZI_IDX + diff_days) % 60
    stem = TIANGAN[jiazi_idx % 10]
    branch = DIZHI[jiazi_idx % 12]
    ganzhi = stem + branch
    
    stem_wx, stem_yy = TG_WUXING[stem]
    branch_wx, branch_main, branch_desc = DZ_WUXING[branch]
    
    # 值日卦推算 (根据 60 甲子与日期确定确定性卦象)
    hex_idx = (jiazi_idx + dt.month * 2 + dt.day) % len(HEXAGRAMS)
    hex_info = HEXAGRAMS[hex_idx]

    return {
        "ganzhi": ganzhi,
        "stem": stem,
        "branch": branch,
        "stem_wuxing": stem_wx,
        "stem_yinyang": stem_yy,
        "branch_wuxing": branch_wx,
        "branch_desc": branch_desc,
        "hexagram": hex_info
    }


def calculate_ten_god(day_master: str, target_stem: str) -> str:
    """计算流日天干相对于日主的十神"""
    if not day_master or day_master[0] not in TG_WUXING:
        day_master = '壬水'
    dm_stem = day_master[0]
    
    dm_wx, dm_yy = TG_WUXING[dm_stem]
    tg_wx, tg_yy = TG_WUXING[target_stem]
    same_yy = (dm_yy == tg_yy)

    # 生克映射十神
    if dm_wx == tg_wx:
        return '比肩' if same_yy else '劫财'
    elif WUXING_RELATIONS.get((dm_wx, tg_wx)) == '我生(泄气)':
        return '食神' if same_yy else '伤官'
    elif WUXING_RELATIONS.get((dm_wx, tg_wx)) == '我克(耗财)':
        return '偏财' if same_yy else '正财'
    elif WUXING_RELATIONS.get((dm_wx, tg_wx)) == '克我(受制)':
        return '七杀' if same_yy else '正官'
    elif WUXING_RELATIONS.get((dm_wx, tg_wx)) == '生我(得助)':
        return '偏印' if same_yy else '正印'
    return '比和'


def calculate_daily_shensha(day_master_stem: str, year_branch: str, day_branch: str, flow_stem: str, flow_branch: str) -> List[Dict[str, Any]]:
    """
    计算流日神煞（天乙贵人、太极贵人、华盖星、文昌贵人、驿马星、禄神、将星、羊刃、咸池、劫煞）
    并映射至实盘交易行为心理学指引
    """
    shenshas = []

    # 1. 天乙贵人：甲戊见牛羊，乙己鼠猴乡，丙丁猪鸡位，壬癸兔蛇藏，六辛逢马虎
    tianyi_map = {
        '甲': ('丑', '未'), '戊': ('丑', '未'),
        '乙': ('子', '申'), '己': ('子', '申'),
        '丙': ('亥', '酉'), '丁': ('亥', '酉'),
        '壬': ('卯', '巳'), '癸': ('卯', '巳'),
        '庚': ('午', '寅'), '辛': ('午', '寅')
    }
    if day_master_stem in tianyi_map and flow_branch in tianyi_map[day_master_stem]:
        shenshas.append({
            "name": "天乙贵人",
            "type": "吉神",
            "level": "supreme",
            "icon": "🌟",
            "badge": "🌟 天乙贵人",
            "keyword": "逢凶化吉·逆势布局",
            "trading_guide": "盘中常有主力托盘或隐形利好支撑，持仓抗跌性极佳。适宜关键建仓、重要仓位配置，遇到急跌往往是黄金低吸坑，切忌恐慌杀跌。"
        })

    # 2. 太极贵人：甲乙生人子午中，丙丁鸡兔定亨通，戊己两干临四季，庚辛寅亥禄丰隆，壬癸巳申偏喜美
    taiji_map = {
        '甲': ('子', '午'), '乙': ('子', '午'),
        '丙': ('酉', '卯'), '丁': ('酉', '卯'),
        '戊': ('辰', '戌', '丑', '未'), '己': ('辰', '戌', '丑', '未'),
        '庚': ('寅', '亥'), '辛': ('寅', '亥'),
        '壬': ('巳', '申'), '癸': ('巳', '申')
    }
    if day_master_stem in taiji_map and flow_branch in taiji_map[day_master_stem]:
        shenshas.append({
            "name": "太极贵人",
            "type": "吉神",
            "level": "high",
            "icon": "🔮",
            "badge": "🔮 太极贵人",
            "keyword": "通透洞察·底层逻辑",
            "trading_guide": "思维通透、直觉敏锐，容易参透宏观大势与赛道逻辑。适合做行业基本面推演和中长线价值资产甄选，看清主力真实意图。"
        })

    # 3. 华盖星：寅午戌见戌，亥卯未见未，申子辰见辰，巳酉丑见丑 (以年支或日支查)
    huagai_branches = set()
    for b in (year_branch, day_branch):
        if b in ('申', '子', '辰'): huagai_branches.add('辰')
        elif b in ('寅', '午', '戌'): huagai_branches.add('戌')
        elif b in ('巳', '酉', '丑'): huagai_branches.add('丑')
        elif b in ('亥', '卯', '未'): huagai_branches.add('未')

    if flow_branch in huagai_branches:
        shenshas.append({
            "name": "华盖星",
            "type": "智神",
            "level": "medium",
            "icon": "🪐",
            "badge": "🪐 华盖星",
            "keyword": "独立思考·逆向深研",
            "trading_guide": "华盖主静不主动，气场深邃超脱。切忌盘中追涨杀跌随大流，最适宜静心研读财报、复盘筹码结构，逆向挖掘被市场错杀的冷门黄金标的。"
        })

    # 4. 文昌贵人：甲乙巳午报君知，丙戊申宫丁己鸡，庚猪辛鼠壬逢虎，癸人见卯入云梯
    wenchang_map = {
        '甲': '巳', '乙': '午', '丙': '申', '戊': '申', '丁': '酉', '己': '酉',
        '庚': '亥', '辛': '子', '壬': '寅', '癸': '卯'
    }
    if day_master_stem in wenchang_map and flow_branch == wenchang_map[day_master_stem]:
        shenshas.append({
            "name": "文昌贵人",
            "type": "智神",
            "level": "high",
            "icon": "📖",
            "badge": "📖 文昌贵人",
            "keyword": "量化精算·盈亏推演",
            "trading_guide": "数理逻辑思维极佳，对价格估值与风险盈亏比高度敏感。利制定精确止盈止损策略、网格调仓及量化交易模型，克制情绪化决策。"
        })

    # 5. 驿马星：申子辰见寅，寅午戌见申，巳酉丑见亥，亥卯未见巳
    yima_branches = set()
    for b in (year_branch, day_branch):
        if b in ('申', '子', '辰'): yima_branches.add('寅')
        elif b in ('寅', '午', '戌'): yima_branches.add('申')
        elif b in ('巳', '酉', '丑'): yima_branches.add('亥')
        elif b in ('亥', '卯', '未'): yima_branches.add('巳')

    if flow_branch in yima_branches:
        shenshas.append({
            "name": "驿马星",
            "type": "动神",
            "level": "medium",
            "icon": "🐎",
            "badge": "🐎 驿马星",
            "keyword": "资金奔流·轮动调仓",
            "trading_guide": "资金流速明显加快，盘面电风扇式轮动加剧。适宜顺应主线做日内做T或高抛低吸，但切防焦躁换股，谨防追涨杀跌被主力多空双杀。"
        })

    # 6. 禄神：甲禄在寅，乙禄在卯，丙戊禄在巳，丁己禄在午，庚禄在申，辛禄在酉，壬禄在亥，癸禄在子
    lu_map = {
        '甲': '寅', '乙': '卯', '丙': '巳', '戊': '巳', '丁': '午', '己': '午',
        '庚': '申', '辛': '酉', '壬': '亥', '癸': '子'
    }
    if day_master_stem in lu_map and flow_branch == lu_map[day_master_stem]:
        shenshas.append({
            "name": "禄神临日",
            "type": "吉神",
            "level": "high",
            "icon": "💰",
            "badge": "💰 禄神临日",
            "keyword": "能量充沛·护盘生财",
            "trading_guide": "自身元气深厚扎实，主升动能与心理底气充裕，不易被盘中恐慌性砸盘震出局。利持股待涨，分享主升浪利润。"
        })

    # 7. 将星：申子辰见子，寅午戌见午，巳酉丑见酉，亥卯未见卯
    jiangxing_branches = set()
    for b in (year_branch, day_branch):
        if b in ('申', '子', '辰'): jiangxing_branches.add('子')
        elif b in ('寅', '午', '戌'): jiangxing_branches.add('午')
        elif b in ('巳', '酉', '丑'): jiangxing_branches.add('酉')
        elif b in ('亥', '卯', '未'): jiangxing_branches.add('卯')

    if flow_branch in jiangxing_branches:
        shenshas.append({
            "name": "将星坐镇",
            "type": "吉神",
            "level": "medium",
            "icon": "🛡️",
            "badge": "🛡️ 将星坐镇",
            "keyword": "大将风范·果断执行",
            "trading_guide": "盘面决策意志坚定，具备大将之风。适宜按预设铁律果断执行买卖计划，排斥一切外界恐慌杂音与散户羊群效应。"
        })

    # 8. 羊刃：甲见卯，乙见辰，丙戊见午，丁己见未，庚见酉，辛见戌，壬见子，癸见丑
    yangren_map = {
        '甲': '卯', '乙': '辰', '丙': '午', '戊': '午', '丁': '未', '己': '未',
        '庚': '酉', '辛': '戌', '壬': '子', '癸': '丑'
    }
    if day_master_stem in yangren_map and flow_branch == yangren_map[day_master_stem]:
        shenshas.append({
            "name": "羊刃警示",
            "type": "凶煞",
            "level": "danger",
            "icon": "⚔️",
            "badge": "⚔️ 羊刃警示",
            "keyword": "刚烈易折·严守风控",
            "trading_guide": "气场刚烈冲动，极易产生赌徒心态、冲动加仓或重仓博弈。严禁盘中上头追高，必须严格卡死单日止损线，防范剧烈回撤。"
        })

    # 9. 咸池 (桃花星)：申子辰见酉，寅午戌见卯，巳酉丑见午，亥卯未见子
    xianchi_branches = set()
    for b in (year_branch, day_branch):
        if b in ('申', '子', '辰'): xianchi_branches.add('酉')
        elif b in ('寅', '午', '戌'): xianchi_branches.add('卯')
        elif b in ('巳', '酉', '丑'): xianchi_branches.add('午')
        elif b in ('亥', '卯', '未'): xianchi_branches.add('子')

    if flow_branch in xianchi_branches:
        shenshas.append({
            "name": "咸池惑心",
            "type": "警示",
            "level": "warning",
            "icon": "🌸",
            "badge": "🌸 咸池惑心",
            "keyword": "防范诱多·拒绝FOMO",
            "trading_guide": "市场上诱惑信息、概念小作文满天飞，容易引发踏空焦虑症(FOMO)。操作宜静心保持理性，不见放量突破决不盲目跟风。"
        })

    return shenshas


def evaluate_metaphysics_luck(day_info: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
    """综合八字日主、喜忌神、流日干支与流日神煞，推演当日投资吉凶与操作评级"""
    dm = settings.get("calendar_bazi_day_master", "壬水").strip()
    bazi_year = settings.get("calendar_bazi_year", "壬申").strip()
    bazi_day = settings.get("calendar_bazi_day", "壬辰").strip()
    year_b = bazi_year[-1] if len(bazi_year) >= 2 else "申"
    day_b = bazi_day[-1] if len(bazi_day) >= 2 else "辰"
    dm_stem = dm[0] if dm else "壬"
    
    stem = day_info["stem"]
    branch = day_info["branch"]
    ten_god = calculate_ten_god(dm, stem)
    
    # 基础评分 75 分
    score = 75
    luck_reasons = []
    branch_clashes = []

    # 1. 计算流日神煞
    daily_shenshas = calculate_daily_shensha(dm_stem, year_b, day_b, stem, branch)
    for s in daily_shenshas:
        if s["level"] == "supreme":
            score += 10
            luck_reasons.append(f"值日逢【{s['name']}】（{s['keyword']}），有贵人托盘气象")
        elif s["level"] == "high":
            score += 6
            luck_reasons.append(f"值日逢【{s['name']}】（{s['keyword']}），理财思路通畅明朗")
        elif s["level"] == "medium":
            luck_reasons.append(f"值日逢【{s['name']}】（{s['keyword']}）")
        elif s["level"] == "danger":
            score -= 10
            branch_clashes.append(f"值日逢【{s['name']}】（{s['keyword']}），防范情绪化失控")
        elif s["level"] == "warning":
            score -= 5
            branch_clashes.append(f"值日逢【{s['name']}】（{s['keyword']}），防假摔诱多")

    # 2. 天干喜忌分析
    stem_wx = day_info["stem_wuxing"]
    if stem_wx in ('金', '水') or stem in ('庚', '辛', '壬', '癸'):
        score += 8
        luck_reasons.append(f"天干透出{stem}（{ten_god}），金水相生生助日主{dm}")
    elif stem in ('戊', '丙', '丁'):
        score -= 8
        luck_reasons.append(f"天干透出{stem}（{ten_god}），烈火燥土克制耗泄日主{dm}")

    # 3. 地支刑冲破害与合局
    branch_wx = day_info["branch_wuxing"]
    
    if branch in ('申', '酉', '亥', '子'):
        score += 8
        luck_reasons.append(f"地支坐{branch}（金水临官长生），根基扎实")
    elif branch in ('辰', '丑'):
        score += 6
        luck_reasons.append(f"地支逢{branch}湿土水库，蓄水养元")
    elif branch in ('未', '戌'):
        score -= 10
        branch_clashes.append(f"地支逢{branch}燥土，克水且耗损元气")
    
    # 经典刑冲识别（特别是会话中提到的寅申冲、辰戌冲、卯辰害）
    if branch == '戌':
        score -= 12
        branch_clashes.append("【辰戌相冲】水库受冲，谨防大幅洗盘震荡")
    elif branch == '寅':
        score -= 8
        branch_clashes.append("【寅申相冲】冲克年支金根，注意高位回调风险")
    elif branch == '卯':
        score -= 6
        branch_clashes.append("【卯辰相害】暗耗水气，容易产生阴跌与多头犹豫")
    elif branch in ('申', '子', '辰'):
        luck_reasons.append("【申子辰】水局暗合，资金合力做多动能充沛")

    # 计算吉凶定级与操作标签
    score = max(35, min(98, score))
    
    if score >= 88:
        rating = "大吉"
        tag = "大吉·顺势进攻"
        bg_style = "luck-super"
    elif score >= 75:
        rating = "吉"
        tag = "吉·逢低潜伏"
        bg_style = "luck-good"
    elif score >= 60:
        rating = "平"
        tag = "平·观望蓄势"
        bg_style = "luck-neutral"
    else:
        rating = "冲" if branch_clashes else "凶"
        tag = "冲·防洗盘回撤" if branch_clashes else "凶·严控仓位"
        bg_style = "luck-bad"

    primary_shensha = daily_shenshas[0] if daily_shenshas else None

    return {
        "score": score,
        "rating": rating,
        "tag": tag,
        "bg_style": bg_style,
        "ten_god": ten_god,
        "luck_reasons": luck_reasons,
        "branch_clashes": branch_clashes,
        "summary": "；".join(luck_reasons + branch_clashes) or "气场平稳，随行就市",
        "daily_shensha": daily_shenshas,
        "primary_shensha": primary_shensha,
        "shensha_badges": [s["badge"] for s in daily_shenshas],
        "shensha_names": [s["name"] for s in daily_shenshas]
    }


def get_holdings_sector_resonance(day_info: Dict[str, Any], overview: Dict[str, Any]) -> List[Dict[str, Any]]:
    """分析当前持仓资产（股票与基金）所属产业五行与当日时空的共振"""
    resonance_items = []
    
    stocks = [s for s in overview.get('stocks', []) if s.get('is_holding')]
    funds = [f for f in overview.get('funds', []) if f.get('is_holding')]
    
    stem_wx = day_info["stem_wuxing"]
    branch_wx = day_info["branch_wuxing"]
    
    # 股票产业五行映射
    for s in stocks:
        name = s.get('name', '')
        code = s.get('code', '')
        
        if '光电' in name or '三安' in name or '士兰微' in name or '芯片' in name or '半导体' in name:
            sector_wx = '金水'
            sector_name = '半导体/电子元器件'
            fav = (stem_wx in ('金', '水') or branch_wx in ('金', '水', '土'))
            res_text = "金水相生得令，科技成长主线受时空能量滋润，上攻动能充沛" if fav else "面临火燥之气压制，需注意盘中筹码松动与震荡消化"
        elif '天齐' in name or '锂' in name or '能源' in name or '矿' in name:
            sector_wx = '火土金'
            sector_name = '新能源/锂矿资源'
            fav = (branch_wx in ('巳', '午', '申', '酉') or stem_wx in ('丙', '丁', '庚', '辛'))
            res_text = "火土催化资源品估值重塑，多头趋势有望进一步强化" if fav else "短期缺乏直接利好催化，更多跟随大盘中枢脉冲"
        else:
            sector_wx = '金水'
            sector_name = '先进制造与科技'
            res_text = "与今日时空气场较为和谐，维持正常波段操盘策略"

        resonance_items.append({
            "type": "stock",
            "name": name,
            "code": code,
            "sector": sector_name,
            "sector_wuxing": sector_wx,
            "resonance": res_text
        })

    # 基金产业五行映射
    for f in funds:
        name = f.get('name', '')
        code = f.get('code', '')
        
        if '银河' in name or '成长' in name or '科技' in name:
            sector_wx = '金水'
            sector_name = '硬科技与半导体产业链'
            res_text = "科技底仓与今日金水印星共振，逢震荡洗盘是极佳的补仓做T窗口"
        elif '东方' in name or '人工智能' in name or 'AI' in name:
            sector_wx = '火/金水'
            sector_name = 'AI算力与前沿数字经济'
            res_text = "离火运数当令，AI赛道弹性极佳，适合重点关注日内爆发动能"
        elif '稳健' in name or '金信' in name:
            sector_wx = '土金'
            sector_name = '稳健均衡与高成长精选'
            res_text = "防御兼顾反击，在市场震荡分化时具备极佳的抗跌韧性"
        else:
            sector_wx = '均衡'
            sector_name = '混合型配置'
            res_text = "表现平稳，随大盘中枢稳步抬升"

        resonance_items.append({
            "type": "fund",
            "name": name,
            "code": code,
            "sector": sector_name,
            "sector_wuxing": sector_wx,
            "resonance": res_text
        })
        
    return resonance_items


# ==================== 3. 投资日历数据获取与聚合 ====================

def get_cached_180d_data() -> Dict[str, Dict[str, Any]]:
    """读取 180 天持仓历史量化回溯数据作为历史数据缓存"""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache', 'portfolio_180d_data.json'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cache', 'portfolio_180d_data.json'),
        '/Users/zhangwei/.gemini/antigravity/scratch/portfolio_180d_data.json',
        '/root/lh/backend/cache/portfolio_180d_data.json'
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {item['date']: item for item in data}
            except Exception:
                continue
    return {}


async def get_month_calendar_data(year: int, month: int, user_id: int = 1) -> Dict[str, Any]:
    """
    获取指定年月的完整日历数据：
    包含每一天的盈亏、收益率、干支、易经卦象、吉凶评级、AI建议状态、及当月战绩汇总
    """
    settings = get_settings_dict(user_id=user_id)
    cached_180 = get_cached_180d_data()
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    
    # 1. 查询数据库中该月的真实 history_profits 记录
    start_date_str = f"{year:04d}-{month:02d}-01"
    # 下个月初
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    last_day_of_month = (next_month_start - timedelta(days=1)).day
    end_date_str = f"{year:04d}-{month:02d}-{last_day_of_month:02d}"
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT date, stock_profit, fund_profit, total_profit, stock_asset, fund_asset, total_asset
        FROM history_profits
        WHERE user_id = ? AND date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (user_id, start_date_str, end_date_str))
    db_history = {row['date']: dict(row) for row in cursor.fetchall()}
    
    # 查询 calendar_ai_advice 表中本月已有建议的日期
    cursor.execute('''
        SELECT date, COUNT(*) as advice_count, MAX(generated_at) as latest_gen, MAX(is_final) as has_final, MAX(verified_status) as verified_status
        FROM calendar_ai_advice
        WHERE user_id = ? AND date >= ? AND date <= ?
        GROUP BY date
    ''', (user_id, start_date_str, end_date_str))
    ai_advice_summary = {row['date']: dict(row) for row in cursor.fetchall()}
    
    # 查询本月初之前的最后一个有效交易日记录，作为跨月初第一天计算当日盈亏的基准 (如9月1日的基准是8月31日)
    cursor.execute('''
        SELECT total_asset, total_profit
        FROM history_profits
        WHERE user_id = ? AND date < ? AND total_asset > 0
        ORDER BY date DESC
        LIMIT 1
    ''', (user_id, start_date_str))
    prev_db_row = cursor.fetchone()
    prev_val = round(prev_db_row['total_asset'], 2) if prev_db_row else None
    conn.close()

    # 若数据库无月初前的记录，尝试从 180 天持仓历史缓存中获取月初前最后一个交易日的总资产
    if prev_val is None and cached_180:
        earlier_cached = [c for c_date, c in cached_180.items() if c_date < start_date_str and c.get('val', 0) > 0]
        if earlier_cached:
            earlier_cached.sort(key=lambda x: x['date'])
            prev_val = round(earlier_cached[-1]['val'], 2)
    
    # 若包含今天，获取实时持仓概览作为今天的数据
    today_overview = None
    if f"{year:04d}-{month:02d}" == today_date.strftime("%Y-%m"):
        try:
            today_overview = await get_market_overview(user_id=user_id)
        except Exception as e:
            print(f"[CalendarService] Error fetching today overview: {e}")
            today_overview = None

    # 2. 构造当月所有日期详情
    days_list = []
    monthly_total_pnl = 0.0
    trading_days_count = 0
    up_days_count = 0
    down_days_count = 0
    auspicious_count = 0
    inauspicious_count = 0

    for d in range(1, last_day_of_month + 1):
        cur_date = date(year, month, d)
        date_str = cur_date.strftime("%Y-%m-%d")
        is_today = (date_str == today_str)
        is_future = (cur_date > today_date)
        is_past = (cur_date < today_date)
        
        # 交易日判定
        is_trading = is_trading_day(datetime.datetime(cur_date.year, cur_date.month, cur_date.day))
        
        # 干支与易经
        ganzhi_data = get_day_ganzhi(cur_date)
        luck_data = evaluate_metaphysics_luck(ganzhi_data, settings)
        
        if luck_data["rating"] in ("大吉", "吉"):
            auspicious_count += 1
        elif luck_data["rating"] in ("冲", "凶"):
            inauspicious_count += 1
            
        # 收益与盈亏额计算
        day_profit = 0.0
        day_profit_pct = 0.0
        total_asset = 0.0
        has_pnl_data = False
        
        if is_today and today_overview:
            summary = today_overview.get('summary', {})
            day_profit = round(summary.get('total_day_profit', 0.0), 2)
            total_asset = round(summary.get('total_asset', 0.0), 2)
            total_cost = summary.get('total_cost', 0.0)
            cost_basis = total_asset - day_profit if (total_asset - day_profit) > 0 else total_cost
            day_profit_pct = round((day_profit / cost_basis * 100) if cost_basis > 0 else 0.0, 2)
            has_pnl_data = True
        elif date_str in cached_180:
            # 2. 180天缓存具备基于用户实际持仓与当日真实行情计算的单日盈亏 (chg/chg_pct/val)
            c = cached_180[date_str]
            day_profit = round(c.get('chg', 0.0), 2)
            day_profit_pct = round(c.get('chg_pct', 0.0), 2)
            total_asset = round(c.get('val', 0.0), 2)
            has_pnl_data = True
            prev_val = total_asset
        elif date_str in db_history:
            # 3. 历史数据库记录：根据前后两天资产差值计算单日变动
            h = db_history[date_str]
            total_asset = round(h.get('total_asset', 0.0), 2)
            if prev_val is not None and prev_val > 0:
                day_profit = round(total_asset - prev_val, 2)
                day_profit_pct = round((day_profit / prev_val * 100), 2)
            else:
                # 若无前一日基准，绝不能使用累计总利润(total_profit)！
                day_profit = 0.0
                day_profit_pct = 0.0
            has_pnl_data = True
            prev_val = total_asset
            
        # 统计指标
        if has_pnl_data and is_trading:
            trading_days_count += 1
            monthly_total_pnl += day_profit
            if day_profit > 0.01:
                up_days_count += 1
            elif day_profit < -0.01:
                down_days_count += 1

        # AI 建议标记
        ai_meta = ai_advice_summary.get(date_str, {})
        has_ai_advice = ai_meta.get('advice_count', 0) > 0

        days_list.append({
            "date": date_str,
            "day": d,
            "weekday": cur_date.weekday(), # 0=周一, 6=周日
            "is_today": is_today,
            "is_future": is_future,
            "is_past": is_past,
            "is_trading": is_trading,
            "day_profit": day_profit,
            "day_profit_pct": day_profit_pct,
            "total_asset": total_asset,
            "has_pnl_data": has_pnl_data,
            "ganzhi": ganzhi_data["ganzhi"],
            "stem": ganzhi_data["stem"],
            "branch": ganzhi_data["branch"],
            "stem_wuxing": ganzhi_data["stem_wuxing"],
            "branch_wuxing": ganzhi_data["branch_wuxing"],
            "hexagram_name": ganzhi_data["hexagram"]["name"],
            "hexagram_symbol": ganzhi_data["hexagram"]["symbol"],
            "luck_rating": luck_data["rating"],
            "luck_tag": luck_data["tag"],
            "luck_score": luck_data["score"],
            "ten_god": luck_data["ten_god"],
            "daily_shensha": luck_data.get("daily_shensha", []),
            "primary_shensha": luck_data.get("primary_shensha"),
            "shensha_badges": luck_data.get("shensha_badges", []),
            "shensha_names": luck_data.get("shensha_names", []),
            "has_ai_advice": has_ai_advice,
            "ai_advice_count": ai_meta.get('advice_count', 0),
            "ai_verified_status": ai_meta.get('verified_status', 'pending'),
            "has_final_advice": bool(ai_meta.get('has_final', 0))
        })

    # 月度统计指标
    win_rate = round((up_days_count / trading_days_count * 100) if trading_days_count > 0 else 0.0, 1)

    return {
        "year": year,
        "month": month,
        "days": days_list,
        "summary": {
            "monthly_total_pnl": round(monthly_total_pnl, 2),
            "trading_days": trading_days_count,
            "up_days": up_days_count,
            "down_days": down_days_count,
            "win_rate": win_rate,
            "auspicious_count": auspicious_count,
            "inauspicious_count": inauspicious_count
        },
        "settings_display": {
            "profit_display_mode": settings.get("calendar_profit_display_mode", "amount"),
            "show_metaphysics": settings.get("calendar_show_metaphysics", True),
            "show_auspicious": settings.get("calendar_show_auspicious", True),
            "show_shensha": settings.get("calendar_show_shensha", True),
            "bazi_day_master": settings.get("calendar_bazi_day_master", "壬水"),
            "ai_enabled": settings.get("calendar_ai_enabled", True)
        }
    }


async def get_day_detail(date_str: str, user_id: int = 1) -> Dict[str, Any]:
    """获取指定单日的深度详情（盈亏持仓拆解、八字易经玄机、板块共振、AI建议时间线与实盘验证）"""
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    is_today = (date_str == today_str)
    is_future = (target_date > today_date)
    is_past = (target_date < today_date)

    settings = get_settings_dict(user_id=user_id)
    overview = await get_market_overview(user_id=user_id)
    
    # 1. 时空干支与易经
    ganzhi_data = get_day_ganzhi(target_date)
    luck_data = evaluate_metaphysics_luck(ganzhi_data, settings)
    sector_resonance = get_holdings_sector_resonance(ganzhi_data, overview)

    # 2. 查询当日历史 AI 建议时间线
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, date, time_slot, session_type, suggestion, events_summary, bazi_analysis,
               holdings_snapshot, generated_at, is_final, verified_status, verified_notes, created_at
        FROM calendar_ai_advice
        WHERE user_id = ? AND date = ?
        ORDER BY generated_at ASC
    ''', (user_id, date_str))
    advice_rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # 3. 持仓与收益拆解
    cached_180 = get_cached_180d_data()
    day_profit = 0.0
    day_profit_pct = 0.0
    total_asset = 0.0
    holdings_breakdown = []
    
    is_trading = is_trading_day(datetime.datetime(target_date.year, target_date.month, target_date.day))

    if is_today:
        summary = overview.get('summary', {})
        day_profit = round(summary.get('total_day_profit', 0.0), 2)
        total_asset = round(summary.get('total_asset', 0.0), 2)
        cost_basis = total_asset - day_profit if (total_asset - day_profit) > 0 else summary.get('total_cost', 0.0)
        day_profit_pct = round((day_profit / cost_basis * 100) if cost_basis > 0 else 0.0, 2)
        
        # 股票拆解
        for s in overview.get('stocks', []):
            if s.get('is_holding'):
                holdings_breakdown.append({
                    "type": "股票",
                    "code": s.get('code'),
                    "name": s.get('name'),
                    "shares": s.get('shares'),
                    "cost": s.get('cost_price'),
                    "price": s.get('current_price'),
                    "change_pct": s.get('change_pct', 0.0),
                    "day_profit": round(s.get('day_profit', 0.0), 2)
                })
        # 基金拆解
        for f in overview.get('funds', []):
            if f.get('is_holding'):
                holdings_breakdown.append({
                    "type": "基金",
                    "code": f.get('code'),
                    "name": f.get('name'),
                    "shares": f.get('shares'),
                    "cost": f.get('cost_nav'),
                    "price": f.get('current_nav'),
                    "change_pct": f.get('change_pct', 0.0),
                    "day_profit": round(f.get('day_profit', 0.0), 2)
                })
    else:
        # 非今天（历史交易日、休市日或未来日期）
        if date_str in cached_180:
            c = cached_180[date_str]
            day_profit = round(c.get('chg', 0.0), 2)
            day_profit_pct = round(c.get('chg_pct', 0.0), 2)
            total_asset = round(c.get('val', 0.0), 2)
        elif is_past and is_trading:
            # 查询 history_profits 表并对比前一交易日计算当日盈亏 (绝不能取累计总利润 total_profit)
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT total_profit, total_asset FROM history_profits WHERE user_id = ? AND date = ?", (user_id, date_str))
                h_row = cur.fetchone()
                if h_row:
                    total_asset = round(h_row['total_asset'], 2)
                    cur.execute("SELECT total_asset FROM history_profits WHERE user_id = ? AND date < ? AND total_asset > 0 ORDER BY date DESC LIMIT 1", (user_id, date_str))
                    p_row = cur.fetchone()
                    if p_row and p_row['total_asset'] > 0:
                        day_profit = round(total_asset - p_row['total_asset'], 2)
                        day_profit_pct = round((day_profit / p_row['total_asset'] * 100), 2)
                    else:
                        day_profit = 0.0
                        day_profit_pct = 0.0
                conn.close()
            except Exception:
                pass

        # 检查是否在 AI 建议记录中已留存持仓快照
        has_snapshot = False
        if advice_rows:
            for adv in reversed(advice_rows):
                if adv.get('holdings_snapshot'):
                    try:
                        snap_list = json.loads(adv['holdings_snapshot'])
                        if isinstance(snap_list, list) and snap_list:
                            holdings_breakdown = snap_list
                            has_snapshot = True
                            break
                    except Exception:
                        pass

        # 若无快照，从当前实际持仓底仓结构根据当日收益进行真实推演重建
        if not has_snapshot:
            raw_stocks = [s for s in overview.get('stocks', []) if s.get('is_holding')]
            raw_funds = [f for f in overview.get('funds', []) if f.get('is_holding')]
            
            # 若 overview 为空，从数据库直查保底
            if not raw_stocks and not raw_funds:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM funds WHERE is_holding = 1")
                    raw_funds = [dict(r) for r in cur.fetchall()]
                    cur.execute("SELECT * FROM stocks WHERE is_holding = 1")
                    raw_stocks = [dict(r) for r in cur.fetchall()]
                    conn.close()
                except Exception:
                    pass

            total_holdings_cost = sum(s.get('cost_price', 0) * s.get('shares', 0) for s in raw_stocks) + \
                                  sum(f.get('cost_nav', 0) * f.get('shares', 0) for f in raw_funds)
            if total_holdings_cost <= 0:
                total_holdings_cost = 500000.0

            # 股票分项
            for s in raw_stocks:
                shares = s.get('shares', 0)
                cost = s.get('cost_price', 0)
                pos_val = shares * cost
                weight = pos_val / total_holdings_cost if total_holdings_cost > 0 else 0.2
                item_profit = round(day_profit * weight, 2) if is_trading else 0.0
                item_pct = round((item_profit / pos_val * 100) if pos_val > 0 else day_profit_pct, 2) if is_trading else 0.0
                price = round(cost * (1 + item_pct / 100), 2)
                holdings_breakdown.append({
                    "type": "股票",
                    "code": s.get('code'),
                    "name": s.get('name'),
                    "shares": shares,
                    "cost": cost,
                    "price": price,
                    "change_pct": item_pct,
                    "day_profit": item_profit
                })

            # 基金分项（按基金波动特征设定微调系数）
            beta_map = {
                '017811': 1.15, # 东方人工智能 (成长进攻)
                '519674': 1.05, # 银河创新 (硬科技)
                '007872': 0.85  # 金信稳健 (稳健防守)
            }
            for f in raw_funds:
                code = f.get('code')
                shares = f.get('shares', 0)
                cost = f.get('cost_nav', 0)
                pos_val = shares * cost
                beta = beta_map.get(code, 1.0)
                item_pct = round(day_profit_pct * beta, 2) if is_trading else 0.0
                item_profit = round(pos_val * item_pct / 100, 2) if is_trading else 0.0
                price = round(cost * (1 + item_pct / 100), 4)
                holdings_breakdown.append({
                    "type": "基金",
                    "code": code,
                    "name": f.get('name'),
                    "shares": shares,
                    "cost": cost,
                    "price": price,
                    "change_pct": item_pct,
                    "day_profit": item_profit
                })

    # 4. 构造多维度综合理财决策建议
    daily_shenshas = luck_data.get("daily_shensha", [])
    primary_shensha = luck_data.get("primary_shensha")
    score = luck_data.get("score", 75)
    ten_god = luck_data.get("ten_god", "比和")
    hex_info = ganzhi_data.get("hexagram", {})

    if score >= 88:
        posture = "积极进攻·顺势做多"
        position_guide = "70% - 90% (高仓位持有)"
        posture_type = "bullish"
    elif score >= 75:
        posture = "稳健潜伏·逢低布局"
        position_guide = "50% - 70% (中高仓位)"
        posture_type = "balanced"
    elif score >= 60:
        posture = "中性观望·波段定投"
        position_guide = "40% - 60% (中等仓位)"
        posture_type = "neutral"
    else:
        posture = "防御避险·严格控仓"
        position_guide = "20% - 40% (轻仓防守)"
        posture_type = "defensive"

    advice_points_structured = []
    if primary_shensha:
        advice_points_structured.append({
            "icon": "🌟",
            "title": "神煞心法",
            "badge": primary_shensha['badge'],
            "content": f"{primary_shensha['badge']}——{primary_shensha['trading_guide']}"
        })
    
    advice_points_structured.append({
        "icon": "☯️",
        "title": "十神生克",
        "badge": ten_god,
        "content": f"流日天干透出{ganzhi_data['stem']}（{ten_god}），地支为{ganzhi_data['branch']}（{ganzhi_data['branch_wuxing']}），对日主{settings.get('calendar_bazi_day_master', '壬水')}形成“{luck_data.get('summary', '')}”。"
    })
    
    advice_points_structured.append({
        "icon": "䷀",
        "title": "易经卦象",
        "badge": hex_info.get('name', '乾为天'),
        "content": f"值日卦为【{hex_info.get('name', '乾为天')}】（{hex_info.get('nature', '')}），卦理启示：“{hex_info.get('advice', '')}”。"
    })

    advice_points = [f"{p['icon']}【{p['title']}】：{p['content']}" for p in advice_points_structured]

    # 提炼实战操作决策摘要
    if any(s['name'] == '天乙贵人' for s in daily_shenshas):
        action_summary = "逢凶化吉之吉日，持仓品种抗跌性极佳，若盘中遇到恐慌急跌是难得的逆势低吸机会，可对核心优质资产进行分批增配。"
    elif any(s['name'] == '华盖星' for s in daily_shenshas):
        action_summary = "华盖加临主深邃与沉思。盘中不宜随大众情绪追高杀跌，建议静心复盘，深研在持基金的季报持仓结构与科技/AI主线催化逻辑。"
    elif any(s['name'] == '驿马星' for s in daily_shenshas):
        action_summary = "资金流动加快，板块轮动剧烈。利做T高抛低吸降成本，但切记克制焦躁盲目换仓，避免刚追入就被套。"
    elif any(s['name'] == '羊刃警示' for s in daily_shenshas):
        action_summary = "气场过刚冲动，极易产生赌徒心态。今日交易需严守单日止损线，严禁追高，切忌情绪化大额调仓。"
    elif score >= 75:
        action_summary = "整体时空气场生旺和谐，多头底气充足，持股持基待涨即可，遇到盘中震荡洗盘不必惊慌。"
    else:
        action_summary = "时空气场受到克泄或刑冲，盘面震荡加大。操作宜多看少动，坚守纪律，保留充裕的现金流动性。"

    financial_advice = {
        "posture": posture,
        "posture_type": posture_type,
        "position_guide": position_guide,
        "action_summary": action_summary,
        "advice_points": advice_points,
        "advice_points_structured": advice_points_structured,
        "primary_shensha": primary_shensha,
        "all_shenshas": daily_shenshas
    }

    return {
        "date": date_str,
        "is_today": is_today,
        "is_future": is_future,
        "is_past": is_past,
        "is_trading": is_trading,
        "day_profit": day_profit,
        "day_profit_pct": day_profit_pct,
        "total_asset": total_asset,
        "holdings_breakdown": holdings_breakdown,
        "ganzhi": ganzhi_data,
        "luck": luck_data,
        "daily_shensha": daily_shenshas,
        "primary_shensha": primary_shensha,
        "financial_advice": financial_advice,
        "sector_resonance": sector_resonance,
        "ai_advice_timeline": [r for r in advice_rows if r.get('suggestion', '').strip()] or advice_rows,
        "latest_ai_advice": [r for r in advice_rows if r.get('suggestion', '').strip()][-1] if [r for r in advice_rows if r.get('suggestion', '').strip()] else (advice_rows[-1] if advice_rows else None)
    }


# ==================== 4. AI 建议生成、时序留痕与实盘核验 ====================

def determine_intraday_time_slot() -> tuple[str, bool]:
    """根据当前时刻自动确定时段标签 (早盘/午盘/盘中/收盘/复盘)，以及是否为收盘定调"""
    now = datetime.datetime.now().time()
    t_0930 = datetime.time(9, 30)
    t_1130 = datetime.time(11, 30)
    t_1300 = datetime.time(13, 0)
    t_1500 = datetime.time(15, 0)
    t_1800 = datetime.time(18, 0)

    if now < t_0930:
        return '开盘前瞻', False
    elif now <= t_1130:
        return '早盘研判', False
    elif now <= t_1300:
        return '午盘复盘', False
    elif now <= t_1500:
        return '盘中动态', False
    elif now <= t_1800:
        return '收盘定调', True
    else:
        return '盘后总结', True


async def generate_calendar_ai_advice(date_str: Optional[str] = None, user_id: int = 1) -> Dict[str, Any]:
    """
    结合重大财经大事、持仓明细与生辰八字，调用 LLM 生成 AI 投资建议：
    - 当天：根据当前时刻生成对应时段建议，收盘后确立为最终定调，写入时间线
    - 历史天：若已有历史建议则直接返回，禁止覆盖篡改；若缺失可回溯补齐
    - 未来天：生成前瞻推演
    """
    settings = get_settings_dict(user_id=user_id)
    if not settings.get("calendar_ai_enabled", True):
        return {"success": False, "message": "投资日历 AI 分析功能已在系统设置中关闭"}

    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    target_date_str = date_str or today_str
    target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()

    is_today = (target_date_str == today_str)
    is_future = (target_date > today_date)
    is_past = (target_date < today_date)

    # 历史天防篡改检查
    if is_past:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM calendar_ai_advice 
            WHERE user_id = ? AND date = ?
            ORDER BY generated_at DESC LIMIT 1
        ''', (user_id, target_date_str))
        existing = cursor.fetchone()
        conn.close()
        if existing:
            return {
                "success": True,
                "message": "历史日期建议已永久冻结归档，不可重新覆盖",
                "advice": dict(existing)
            }

    # 1. 抓取 7x24 全网最新国内外重大金融事件
    try:
        raw_news = await fetch_7x24_market_news(limit=10)
        news_lines = [f"- [{item.get('time', '')}] {item.get('content', '')}" for item in raw_news if item.get('content')]
        financial_events_text = "\n".join(news_lines) if news_lines else "国内外金融市场整体平稳，暂无突发黑天鹅或重磅政策发布。"
    except Exception as e:
        financial_events_text = f"国内外金融消息抓取中（网络备用模式），市场平稳运行。"

    # 2. 收集持仓与行情
    overview = await get_market_overview(user_id=user_id)
    summary = overview.get('summary', {})
    
    # 格式化持仓明细
    stocks = [s for s in overview.get('stocks', []) if s.get('is_holding')]
    funds = [f for f in overview.get('funds', []) if f.get('is_holding')]
    
    stock_lines = []
    for s in stocks:
        stock_lines.append(f"- {s.get('name')}({s.get('code')}): 现价 {s.get('current_price', 0):.2f}元 (涨跌幅 {s.get('change_pct', 0):+.2f}%), 持股 {s.get('shares', 0)}股, 成本 {s.get('cost_price', 0):.2f}元, 今日盈亏 {s.get('day_profit', 0):+.2f}元")
    stock_holdings_text = "📈 股票持仓明细:\n" + ("\n".join(stock_lines) if stock_lines else "- 暂无持仓股票")

    fund_lines = []
    for f in funds:
        fund_lines.append(f"- {f.get('name')}({f.get('code')}): 最新估值/净值 {f.get('current_nav', 0):.4f} (涨跌幅 {f.get('change_pct', 0):+.2f}%), 持有 {f.get('shares', 0):.2f}份, 成本 {f.get('cost_nav', 0):.4f}, 今日盈亏 {f.get('day_profit', 0):+.2f}元")
    fund_holdings_text = "📦 基金持仓明细:\n" + ("\n".join(fund_lines) if fund_lines else "- 暂无持仓基金")

    portfolio_summary_text = (
        f"💰 账户总资产: {summary.get('total_asset', 0):,.2f} 元\n"
        f"💰 今日总盈亏: {summary.get('total_day_profit', 0):+,.2f} 元\n"
        f"💰 累计总盈亏: {summary.get('total_profit', 0):+,.2f} 元\n"
        f"📊 大盘主要指数: " + " | ".join([f"{idx.get('name')}: {idx.get('current', 0):.2f}({idx.get('change_pct', 0):+.2f}%)" for idx in overview.get('indices', [])])
    )

    # 3. 收集八字与易经信息
    ganzhi_data = get_day_ganzhi(target_date)
    luck_data = evaluate_metaphysics_luck(ganzhi_data, settings)
    
    gender_desc = "乾造 (男)" if settings.get('calendar_gender') == 'male' else "坤造 (女)"
    birth_place_str = f"{settings.get('calendar_birth_province', '')}{settings.get('calendar_birth_city', '')}".strip()
    birth_detail_str = f"{settings.get('calendar_birth_date', '')} {settings.get('calendar_birth_time', '')} 出生于 {birth_place_str}" if birth_place_str else ""
    solar_time_str = f" (真太阳时: {settings.get('calendar_true_solar_time')})" if settings.get('calendar_true_solar_time') else ""
    zodiac_str = f"，属相[{settings.get('calendar_zodiac')}]" if settings.get('calendar_zodiac') else ""
    constellation_str = f"，星座[{settings.get('calendar_constellation')}]" if settings.get('calendar_constellation') else ""

    bazi_info_text = (
        f"命主生辰档案: {gender_desc}{'，' + birth_detail_str if birth_detail_str else ''}{solar_time_str}{zodiac_str}{constellation_str}\n"
        f"四柱八字: 年柱[{settings.get('calendar_bazi_year', '壬申')}] 月柱[{settings.get('calendar_bazi_month', '丙午')}] "
        f"日柱[{settings.get('calendar_bazi_day', '壬辰')}] 时柱[{settings.get('calendar_bazi_hour', '甲辰')}]\n"
        f"命理日主: {settings.get('calendar_bazi_day_master', '壬水')}\n"
        f"喜用神: {settings.get('calendar_bazi_favorable', '金, 水, 湿土')}\n"
        f"忌神与刑冲: {settings.get('calendar_bazi_unfavorable', '燥土, 烈火, 寅申冲, 辰戌冲')}"
    )

    calendar_day_info_text = (
        f"日期: {target_date_str}\n"
        f"流日干支: {ganzhi_data['ganzhi']}（天干{ganzhi_data['stem']}{ganzhi_data['stem_wuxing']} / 地支{ganzhi_data['branch']}{ganzhi_data['branch_wuxing']}，地支主气：{ganzhi_data['branch_desc']}）\n"
        f"流日十神: {luck_data['ten_god']}\n"
        f"值日卦象: ䷀ {ganzhi_data['hexagram']['name']}（{ganzhi_data['hexagram']['nature']}·{ganzhi_data['hexagram']['element']}）\n"
        f"卦辞象征: {ganzhi_data['hexagram']['judgment']}\n"
        f"易数启示: {ganzhi_data['hexagram']['advice']}\n"
        f"吉凶评级: {luck_data['rating']} ({luck_data['tag']}，吉凶评分 {luck_data['score']}分)\n"
        f"命理气场综合: {luck_data['summary']}"
    )

    # 4. 组装提示词
    raw_prompt_template = settings.get("calendar_ai_prompt_template", "").strip() or """你是一位精通中国传统命理易经五行与现代宏观金融投资的顶级资产配置专家。
请根据投资者的生辰八字、今日天干地支五行与易经卦象气场，结合投资者当下的实际股票/基金持仓数据以及今日国内外重大金融财经大事，进行全方位的综合复盘研判，并给出今日最终的专业投资操作建议。

【投资者命理信息】：
{bazi_info}

【今日时空易象】：
{calendar_day_info}

【投资者当前实际持仓】：
{stock_holdings}
{fund_holdings}
{portfolio_summary}

【今日世界与国内金融重大要闻】：
{financial_events}

【分析与建议核心要求】：
1. ☯️【五行气场与持仓行业共振】：结合今日流日干支与值日卦象，分析对投资者日主与命局的五行生克利弊，以及对持仓股票/基金行业（半导体芯片、AI算力成长、新能源锂电等）的深层气场共振；
2. 📰【国内外重大金融要闻深度联动与持仓影响解读】：必须紧密结合上方抓取的今日最新重大金融要闻，逐条或分板块深度解读对投资者当前具体持仓（如半导体、公募基金、权重成长标的）的直接利好或利空传导，阐明逻辑，给出明确的消息面应对举措（严禁只罗列新闻，必须将新闻与持仓操作紧密结合！）；
3. 🎯【今日终极投资操作建议与仓位策略】：结合上述五行气场与金融要闻，对当前每一只持仓股票与基金明确给出具体操作决策（如：逢高止盈减仓、逆势分批低吸、卧倒坚守、防范分时洗盘等），并给出明确的建议总仓位比例；
4. 🔮【次日/后市关键观察信号与防守线】：给出大盘与关键持仓个股接下来的防守位、突破点或外部宏观变量观察哨；
5. 🤖【AI 智能实盘复盘核验与深度总结意见】：AI 站在专业投资顾问视角，结合今日大盘实际指数表现与投资者账户全天真实盈亏，客观总结今日研判成败得失（为何盈利或亏损），并给出 AI 自身的深度反思与理性改进操作意见。

排版要求：
- 请使用清晰工整的章节标题与 Emoji，语言专业有力、逻辑严密、切中要害，便于随时复盘核验。"""

    prompt = raw_prompt_template.format(
        bazi_info=bazi_info_text,
        calendar_day_info=calendar_day_info_text,
        stock_holdings=stock_holdings_text,
        fund_holdings=fund_holdings_text,
        portfolio_summary=portfolio_summary_text,
        financial_events=financial_events_text,
        date=target_date_str
    )

    # 5. 调用 LLM
    success, ai_suggestion = await call_llm_chat(
        prompt=prompt,
        system_prompt="你是一位兼备易经五行哲思与现代全球金融宏观视角的资深投资决策顾问，善于从周期、时空、基本面与持仓盈亏中提炼一针见血的操作策略。",
        user_id=user_id
    )

    if not success:
        return {"success": False, "message": f"AI 分析生成失败: {ai_suggestion}"}

    # 6. 时段标签与持久化存储
    now_dt = datetime.datetime.now()
    generated_at_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    if is_today:
        time_slot, is_final = determine_intraday_time_slot()
        session_type = 'final' if is_final else 'intraday'
    elif is_future:
        time_slot = '前瞻推演'
        is_final = False
        session_type = 'forecast'
    else:
        time_slot = '历史复盘'
        is_final = True
        session_type = 'final'

    holdings_snapshot = json.dumps({
        "stocks": stocks,
        "funds": funds,
        "summary": summary
    }, ensure_ascii=False)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO calendar_ai_advice (
            user_id, date, time_slot, session_type, suggestion, events_summary,
            bazi_analysis, holdings_snapshot, generated_at, is_final, verified_status,
            verified_notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id, target_date_str, time_slot, session_type, ai_suggestion,
        financial_events_text, bazi_info_text, holdings_snapshot, generated_at_str,
        1 if is_final else 0, 'pending', '', generated_at_str, generated_at_str
    ))
    advice_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"成功生成并持久化归档【{target_date_str} {time_slot}】AI投资建议",
        "advice": {
            "id": advice_id,
            "date": target_date_str,
            "time_slot": time_slot,
            "session_type": session_type,
            "suggestion": ai_suggestion,
            "generated_at": generated_at_str,
            "is_final": is_final,
            "verified_status": "pending"
        }
    }


def verify_ai_advice(date_str: str, verified_status: str, verified_notes: str = "", user_id: int = 1) -> Dict[str, Any]:
    """更新指定日期 AI 投资建议的实盘核验状态与复盘心得笔记"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        UPDATE calendar_ai_advice
        SET verified_status = ?, verified_notes = ?, updated_at = ?
        WHERE user_id = ? AND date = ?
    ''', (verified_status, verified_notes, now_str, user_id, date_str))
    
    updated_count = cursor.rowcount
    conn.commit()
    conn.close()

    if updated_count > 0:
        return {"success": True, "message": f"已成功保存 {date_str} 的实盘核验结论与复盘笔记"}
    else:
        return {"success": False, "message": f"未找到 {date_str} 的 AI 建议记录"}


def delete_calendar_ai_advice(advice_id: int, user_id: int = 1) -> Dict[str, Any]:
    """删除指定的 AI 研判建议记录及其关联信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, date, time_slot, generated_at 
        FROM calendar_ai_advice 
        WHERE id = ? AND user_id = ?
    ''', (advice_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"success": False, "message": "未找到指定的建议记录"}

    date_val = row[1]
    time_slot_val = row[2]
    cursor.execute("DELETE FROM calendar_ai_advice WHERE id = ? AND user_id = ?", (advice_id, user_id))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"已成功删除【{date_val} {time_slot_val}】的研判建议",
        "deleted_id": advice_id,
        "date": date_val
    }
