"""
公约结构化种子脚本 — 将《化工园区企业入驻环保公约》解析入库
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine
from app.db.models import RegulationClause

REGULATION_DATA = {
    "source": "化工园区企业入驻环保公约",
    "clauses": [
        {
            "article_no": "第一条",
            "chapter": "总则",
            "article_title": "制定目的与依据",
            "content": "为规范入驻企业环境行为，加强园区生态环境管理，预防环境污染事故，保障园区及周边环境安全，根据《环境保护法》《大气污染防治法》《水污染防治法》《固体废物污染环境防治法》《化工园区安全风险排查治理导则》等法律法规及标准规范，结合本园区实际，制定本公约。",
            "keywords": ["制定目的", "法律依据", "环保法", "大气污染防治", "水污染防治", "固废", "化工园区安全"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第二条",
            "chapter": "总则",
            "article_title": "适用范围",
            "content": "本公约适用于所有入驻本园区的新建、改建、扩建化工企业及现有企业的环保管理行为。",
            "keywords": ["适用范围", "新建", "改建", "扩建", "入驻企业"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第三条",
            "chapter": "总则",
            "article_title": "企业环保主体责任",
            "content": "入驻企业应严格遵守国家及地方环境保护法律法规，落实环境保护主体责任，建立健全环境管理制度，确保污染物稳定达标排放，防范环境风险。",
            "keywords": ["主体责任", "环境管理制度", "达标排放", "环境风险"],
            "action_required": {"type": "establish_system", "items": ["环境管理制度", "污染物达标排放", "环境风险防范"]},
            "platform_url": None,
        },
        {
            "article_no": "第四条",
            "chapter": "污染源在线监控与数据传输",
            "article_title": "在线监测设备安装与对接",
            "content": "入驻企业应按照规定安装、使用大气和水污染物排放自动监测设备，并与园区智慧环保平台实现数据对接。",
            "keywords": ["在线监测", "大气", "废水", "自动监测设备", "智慧环保平台", "数据对接"],
            "action_required": {"type": "install_equipment", "items": ["大气自动监测设备", "水污染物自动监测设备"]},
            "platform_url": None,
        },
        {
            "article_no": "第五条",
            "chapter": "污染源在线监控与数据传输",
            "article_title": "数据传输标准与参数",
            "content": "在线监测设备应按照HJ 212-2017《污染物在线监控（监测）系统数据传输标准》进行数据传输，具体对接参数如下：平台地址：183.93.165.90，废气排放端口号：30541，废水、雨水排放端口号：30542。",
            "keywords": ["HJ 212", "数据传输", "端口号", "废气", "废水", "雨水", "平台地址"],
            "action_required": {
                "type": "configure_platform",
                "items": ["HJ 212-2017 协议配置"],
                "platform_params": {
                    "address": "183.93.165.90",
                    "gas_port": 30541,
                    "water_port": 30542,
                },
            },
            "platform_url": "183.93.165.90",
        },
        {
            "article_no": "第六条",
            "chapter": "污染源在线监控与数据传输",
            "article_title": "监测设备运行维护",
            "content": "企业应确保在线监测设备正常运行，定期开展校准、维保和比对监测，保存相关记录备查。因设备检修、故障等原因需要停运的，应提前向园区环保部门报告，并采取临时监测措施。",
            "keywords": ["设备运行", "校准", "维保", "比对监测", "停运报告"],
            "action_required": {"type": "maintenance", "items": ["定期校准", "设备维保", "比对监测", "停运提前报告"]},
            "platform_url": None,
        },
        {
            "article_no": "第七条",
            "chapter": "污染源在线监控与数据传输",
            "article_title": "数据真实性禁止条款",
            "content": "严禁弄虚作假、篡改或伪造监测数据，严禁擅自停运、拆除、改动在线监测设备及配套设施。",
            "keywords": ["弄虚作假", "篡改数据", "伪造数据", "擅自停运", "拆除设备"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第八条",
            "chapter": "环境信息填报与公开",
            "article_title": "环保专员配备",
            "content": "入驻企业应配备专职或兼职环保专员，负责环境信息填报及日常环境管理工作。",
            "keywords": ["环保专员", "环境信息填报", "日常管理"],
            "action_required": {"type": "staff", "items": ["配备专职或兼职环保专员"]},
            "platform_url": None,
        },
        {
            "article_no": "第九条",
            "chapter": "环境信息填报与公开",
            "article_title": "环境信息填报内容",
            "content": "企业环保专员应按照园区智慧一体化平台要求，及时、准确填报以下信息：1.企业基础档案信息（包括企业基本信息、生产工艺、原辅材料、产排污环节等）；2.危险废物产生、贮存、转移、处置数据；3.自行监测方案及监测数据；4.污染物排放数据；5.环境隐患排查与整改记录；6.其他园区要求的环保信息。",
            "keywords": ["填报内容", "企业档案", "危险废物", "自行监测", "排放数据", "隐患排查", "整改记录"],
            "action_required": {"type": "report_data", "items": ["企业基础档案信息", "危废产生/贮存/转移/处置数据", "自行监测方案及数据", "污染物排放数据", "隐患排查与整改记录"]},
            "platform_url": None,
        },
        {
            "article_no": "第十条",
            "chapter": "环境信息填报与公开",
            "article_title": "环境信息公开",
            "content": "企业应按照《企业环境信息依法披露管理办法》要求，依法公开环境信息，接受社会监督。",
            "keywords": ["信息公开", "社会监督", "披露管理办法"],
            "action_required": {"type": "public_disclosure", "items": ["依法公开环境信息"]},
            "platform_url": None,
        },
        {
            "article_no": "第十一条",
            "chapter": "水污染物排放管理",
            "article_title": "雨污分流与纳管要求",
            "content": "入驻企业应实行雨污分流、清污分流。废水经预处理达到园区纳管标准后，通过一企一管管网输送至园区污水处理厂深度处理。",
            "keywords": ["雨污分流", "清污分流", "一企一管", "纳管标准", "预处理"],
            "action_required": {"type": "wastewater_treatment", "items": ["雨污分流改造", "清污分流改造", "预处理设施达标", "一企一管对接"]},
            "platform_url": None,
        },
        {
            "article_no": "第十二条",
            "chapter": "水污染物排放管理",
            "article_title": "废水排放口对接要求",
            "content": "企业废水排放需与园区一企一管管廊对接；一企一管管径为DN100mm；废水输送压力需达到0.4Mpa以上；企业应在排放口设置流量计、采样口及在线监测设备。",
            "keywords": ["一企一管", "DN100mm", "0.4Mpa", "流量计", "采样口", "在线监测"],
            "action_required": {"type": "pipe_connection", "items": ["一企一管对接", "管径DN100mm", "输送压力>=0.4Mpa", "流量计", "采样口", "在线监测设备"]},
            "platform_url": None,
        },
        {
            "article_no": "第十三条",
            "chapter": "水污染物排放管理",
            "article_title": "雨水排口管理",
            "content": "雨水排口末端应建设明沟，便于观察晴天雨水流动情况，确认无异常后通过明沟排入雨水管网；雨水排口应设置阀门或挡板，初期雨水应导入事故应急池或初期雨水池；雨水排口应设置标识标牌，标明排口编号、排放去向、环保负责人等信息。",
            "keywords": ["雨水排口", "明沟", "阀门", "挡板", "初期雨水", "事故应急池", "标识标牌"],
            "action_required": {"type": "rainwater_management", "items": ["建设雨水排口明沟", "设置阀门/挡板", "初期雨水导入应急池/初期雨水池", "设置标识标牌"]},
            "platform_url": None,
        },
        {
            "article_no": "第十四条",
            "chapter": "水污染物排放管理",
            "article_title": "废水预处理达标要求",
            "content": "企业应加强废水预处理设施运行管理，确保废水稳定达标排放。有毒有害污染物应在车间或车间处理设施排放口达标。",
            "keywords": ["预处理", "达标排放", "有毒有害污染物", "车间排放口"],
            "action_required": {"type": "pretreatment", "items": ["预处理设施运行管理", "有毒有害污染物车间达标"]},
            "platform_url": None,
        },
        {
            "article_no": "第十五条",
            "chapter": "大气污染物排放管理",
            "article_title": "无组织排放管控",
            "content": "入驻企业应加强无组织排放管控，生产工艺废气应收集处理后达标排放。",
            "keywords": ["无组织排放", "生产工艺废气", "收集处理", "达标排放"],
            "action_required": {"type": "fugitive_emission_control", "items": ["无组织排放管控", "废气收集处理"]},
            "platform_url": None,
        },
        {
            "article_no": "第十六条",
            "chapter": "大气污染物排放管理",
            "article_title": "废气排放口标识要求",
            "content": "废气排放口应按照规定设置永久性采样口、采样平台及监测孔，并设置标识标牌，标明：排放口编号、主要污染因子、排放限值、环保负责人姓名及联系方式。",
            "keywords": ["废气排放口", "采样口", "采样平台", "监测孔", "标识标牌", "排放限值"],
            "action_required": {"type": "smokestack_signage", "items": ["设置永久性采样口", "采样平台", "监测孔", "标识标牌（编号/因子/限值/负责人/联系方式）"]},
            "platform_url": None,
        },
        {
            "article_no": "第十七条",
            "chapter": "大气污染物排放管理",
            "article_title": "VOCs治理要求",
            "content": "企业应加强VOCs治理，涉VOCs排放的生产工序应密闭收集，治理设施应与生产设备同步运行，优先采用高效的末端治理技术。",
            "keywords": ["VOCs", "密闭收集", "同步运行", "末端治理"],
            "action_required": {"type": "vocs_control", "items": ["涉VOCs工序密闭收集", "治理设施与生产设备同步运行", "采用高效末端治理技术"]},
            "platform_url": None,
        },
        {
            "article_no": "第十八条",
            "chapter": "固体废物管理",
            "article_title": "固废全过程管理",
            "content": "入驻企业应严格按照《中华人民共和国固体废物污染环境防治法》要求，加强固体废物全过程管理。",
            "keywords": ["固体废物", "全过程管理", "固废法"],
            "action_required": {"type": "solid_waste_management", "items": ["固废全过程管理"]},
            "platform_url": None,
        },
        {
            "article_no": "第十九条",
            "chapter": "固体废物管理",
            "article_title": "危险废物管理要求",
            "content": "危险废物管理要求：1.危废仓库应设置在地势较低、防渗防漏的区域，远离明火及热源；2.危废仓库应设置危废贮存标志牌、危废分区标志牌，正确张贴危险废物标签；3.危废规范化管理相关制度应上墙公示；4.危废暂存应分类收集、分类存放，不同类别危废不得混合贮存；5.危废转移应执行危险废物转移联单制度，通过国家固体废物管理信息系统申报。",
            "keywords": ["危险废物", "危废仓库", "防渗防漏", "标志牌", "分类贮存", "转移联单", "固废管理系统"],
            "action_required": {"type": "hazardous_waste_management", "items": ["危废仓库选址（地势低、防渗防漏、远离明火热源）", "设置危废贮存标志牌及分区标志牌", "张贴危险废物标签", "危废管理制度上墙公示", "分类收集、分类存放，禁止混合贮存", "执行危废转移联单制度", "通过国家固废管理系统申报"]},
            "platform_url": "https://plates.epb.gov.cn/",
        },
        {
            "article_no": "第二十条",
            "chapter": "固体废物管理",
            "article_title": "一般工业固废管理",
            "content": "一般工业固体废物应按照分类收集、资源化利用或规范处置的原则进行管理，不得擅自倾倒、堆放、丢弃。",
            "keywords": ["一般工业固废", "分类收集", "资源化利用", "规范处置"],
            "action_required": {"type": "industrial_waste", "items": ["分类收集", "资源化利用或规范处置", "禁止擅自倾倒堆放"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十一条",
            "chapter": "视频监控系统建设",
            "article_title": "监控重点区域",
            "content": "入驻企业应在以下重点区域安装视频监控设备，并将视频画面接入园区智慧环保平台：1.雨水排放口；2.废水排放口；3.废气排放口；4.危险废物仓库；5.污水处理设施；6.其他园区要求的重点区域。",
            "keywords": ["视频监控", "雨水排口", "废水排口", "废气排口", "危废仓库", "污水处理设施"],
            "action_required": {"type": "video_monitoring", "items": ["雨水排放口监控", "废水排放口监控", "废气排放口监控", "危废仓库监控", "污水处理设施监控", "接入园区智慧环保平台"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十二条",
            "chapter": "视频监控系统建设",
            "article_title": "视频监控系统技术要求",
            "content": "视频监控系统应满足以下技术要求：1.具备实时监控功能，园区平台可随时查看；2.具备视频回放功能，视频数据保存时间不少于30天；3.监控画面应清晰，能够清晰识别作业行为和环保设施运行情况；4.应具备夜间红外监控功能。",
            "keywords": ["实时监控", "视频回放", "30天", "红外监控", "画面清晰"],
            "action_required": {"type": "video_requirements", "items": ["实时监控（园区平台可查）", "视频回放（保存>=30天）", "画面清晰可识别行为", "夜间红外监控"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十三条",
            "chapter": "视频监控系统建设",
            "article_title": "视频设备维护",
            "content": "企业应定期维护视频监控系统，确保设备正常运行。因设备故障等原因需要停运的，应及时修复并向园区环保部门报告。",
            "keywords": ["视频监控维护", "设备故障", "停运报告"],
            "action_required": {"type": "video_maintenance", "items": ["定期维护", "故障及时修复", "停运报告园区环保部门"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十四条",
            "chapter": "标识标牌规范",
            "article_title": "排放口标识标牌",
            "content": "雨水排放口、废水排放口、废气排放口应设置规范化标识标牌；标识标牌应标明：排口编号、主要污染因子、排放限值、环保负责人姓名及联系方式；标识标牌应坚固耐用，设置位置明显，便于识别和监督。",
            "keywords": ["标识标牌", "排口编号", "污染因子", "排放限值", "环保负责人"],
            "action_required": {"type": "signage", "items": ["雨水/废水/废气排放口规范化标识标牌", "标明：编号/因子/限值/负责人/联系方式", "坚固耐用、位置明显"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十五条",
            "chapter": "标识标牌规范",
            "article_title": "应急池/初期雨水池标识",
            "content": "事故应急池、初期雨水池标识牌应标明：设施名称及负责人信息、有效容积（m³）、使用状态（空置/使用中）、Emergency contact information。",
            "keywords": ["事故应急池", "初期雨水池", "标识牌", "有效容积", "使用状态"],
            "action_required": {"type": "emergency_pool_signage", "items": ["设施名称及负责人", "有效容积（m³）", "使用状态（空置/使用中）", "应急联系方式"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十六条",
            "chapter": "标识标牌规范",
            "article_title": "危废贮存设施标识",
            "content": "危险废物贮存设施标识应按照国家《危险废物识别标志设置技术规范》（HJ 1276-2022）要求设置，包括：危废贮存设施整体标志牌、危废分区标志牌、危险废物包装标签、危废规范化管理制度公示牌。",
            "keywords": ["危废标识", "HJ 1276", "2022", "整体标志牌", "分区标志牌", "包装标签", "管理制度公示牌"],
            "action_required": {"type": "hazardous_waste_signage", "items": ["危废贮存设施整体标志牌", "危废分区标志牌", "危险废物包装标签", "危废规范化管理制度公示牌", "符合 HJ 1276-2022 规范"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十七条",
            "chapter": "环境风险防控与应急管理",
            "article_title": "环境风险评估",
            "content": "入驻企业应开展环境风险评估，编制环境风险评估报告，建立环境风险防控体系。",
            "keywords": ["环境风险评估", "风险评估报告", "风险防控体系"],
            "action_required": {"type": "risk_assessment", "items": ["开展环境风险评估", "编制环境风险评估报告", "建立环境风险防控体系"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十八条",
            "chapter": "环境风险防控与应急管理",
            "article_title": "事故应急池与初期雨水收集系统",
            "content": "企业应建设事故应急池和初期雨水收集系统，确保事故状态下的废水、雨水得到有效收集和处理，防止污染物外排。",
            "keywords": ["事故应急池", "初期雨水收集系统", "污染物外排"],
            "action_required": {"type": "emergency_facilities", "items": ["建设事故应急池", "建设初期雨水收集系统", "事故状态废水/雨水有效收集处理"]},
            "platform_url": None,
        },
        {
            "article_no": "第二十九条",
            "chapter": "环境风险防控与应急管理",
            "article_title": "应急预案编制与演练",
            "content": "企业应编制突发环境事件应急预案，报园区环保部门备案，并定期组织应急演练。",
            "keywords": ["应急预案", "备案", "应急演练"],
            "action_required": {"type": "emergency_plan", "items": ["编制突发环境事件应急预案", "报园区环保部门备案", "定期组织应急演练"]},
            "platform_url": None,
        },
        {
            "article_no": "第三十条",
            "chapter": "环境风险防控与应急管理",
            "article_title": "应急物资配备",
            "content": "企业应配备必要的应急物资和设备，建立应急物资台账，定期检查和更新。",
            "keywords": ["应急物资", "应急设备", "台账", "检查更新"],
            "action_required": {"type": "emergency_supplies", "items": ["配备应急物资和设备", "建立应急物资台账", "定期检查更新"]},
            "platform_url": None,
        },
        {
            "article_no": "第三十一条",
            "chapter": "环境风险防控与应急管理",
            "article_title": "事故报告与处置",
            "content": "发生事故或异常情况时，企业应立即启动应急预案，采取措施控制污染，并及时向园区环保部门报告。",
            "keywords": ["事故报告", "异常情况", "应急预案启动", "控制污染"],
            "action_required": {"type": "incident_response", "items": ["立即启动应急预案", "采取措施控制污染", "及时向园区环保部门报告"]},
            "platform_url": None,
        },
        {
            "article_no": "第三十二条",
            "chapter": "监督检查与违约责任",
            "article_title": "接受监督检查",
            "content": "入驻企业应自觉接受园区管理部门的监督检查，如实提供有关情况和材料。",
            "keywords": ["监督检查", "如实提供材料"],
            "action_required": {"type": "inspection_cooperation", "items": ["自觉接受监督检查", "如实提供情况和材料"]},
            "platform_url": None,
        },
        {
            "article_no": "第三十三条",
            "chapter": "监督检查与违约责任",
            "article_title": "违约处理措施",
            "content": "企业违反本公约规定的，园区管理部门可采取以下措施：1.责令限期整改；2.约谈企业负责人；3.通报批评；4.情节严重的，按照相关法律法规严肃处理；5.纳入企业环境信用评价体系。",
            "keywords": ["违约处理", "限期整改", "约谈", "通报批评", "环境信用评价"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第三十四条",
            "chapter": "监督检查与违约责任",
            "article_title": "从严处理情形",
            "content": "企业存在以下行为的，从严处理：1.伪造、篡改监测数据的；2.擅自停运、拆除环保设施的；3.逃避监管排放污染物的；4.发生环境污染事故隐瞒不报的；5.其他严重环境违法行为。",
            "keywords": ["从严处理", "伪造数据", "篡改数据", "擅自停运", "逃避监管", "隐瞒事故"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第三十五条",
            "chapter": "附则",
            "article_title": "未尽事宜",
            "content": "本公约未尽事宜，按照国家及地方相关法律法规执行。",
            "keywords": ["未尽事宜", "法律法规"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第三十六条",
            "chapter": "附则",
            "article_title": "解释权",
            "content": "本公约由园区管理委员会负责解释。",
            "keywords": ["解释权", "园区管理委员会"],
            "action_required": None,
            "platform_url": None,
        },
        {
            "article_no": "第三十七条",
            "chapter": "附则",
            "article_title": "施行日期",
            "content": "本公约自发布之日起施行。",
            "keywords": ["施行日期", "发布"],
            "action_required": None,
            "platform_url": None,
        },
    ],
}


def seed_regulations(db: Session):
    """将公约条款种子数据写入数据库"""
    count = 0
    for clause_data in REGULATION_DATA["clauses"]:
        existing = db.query(RegulationClause).filter(
            RegulationClause.source == REGULATION_DATA["source"],
            RegulationClause.article_no == clause_data["article_no"],
        ).first()
        if existing:
            continue

        clause = RegulationClause(
            source=REGULATION_DATA["source"],
            chapter=clause_data["chapter"],
            article_no=clause_data["article_no"],
            article_title=clause_data["article_title"],
            content=clause_data["content"],
            keywords=clause_data.get("keywords", []),
            action_required=clause_data.get("action_required"),
            platform_url=clause_data.get("platform_url"),
        )
        db.add(clause)
        count += 1

    db.commit()
    return {"message": f"公约条款入库完成，新增 {count} 条", "total": count}


if __name__ == "__main__":
    # Ensure tables exist
    from app.db.models import Base
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        result = seed_regulations(db)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()
