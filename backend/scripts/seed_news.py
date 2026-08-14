# -*- coding: utf-8 -*-
"""
环保资讯大规模种子数据
覆盖：化工园区/环保/医药/新材料/新能源/日用化妆品/复合材料等行业
"""
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import SessionLocal
from app.db.models import NewsItem


def seed_news_batch():
    db = SessionLocal()
    try:
        existing = db.query(NewsItem).count()
        if existing >= 50:
            print(f"Existing {existing} news items, skipping")
            return existing

        news_items = [
            NewsItem(title="生态环境部：化工园区将实施更严格的环境风险管控", source="生态环境部", category="政策解读",
                     summary="生态环境部近日印发化工园区环境风险防控建设规范，要求所有化工园区建立环境风险预警系统。",
                     content="生态环境部近日印发《化工园区环境风险防控建设规范》，要求所有化工园区在2024年底前完成环境风险隐患排查整治，建立健全园区级环境应急体系。规范明确了化工园区集中污水处理设施、危废处置设施的建设标准和管理要求。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 15)),
            NewsItem(title="全国化工园区转型升级加速，环保投资占比持续提升", source="中国化工园区网", category="行业动态",
                     summary="2025年数据显示，全国认定的化工园区环保基础设施投资同比增长23%。",
                     content="据中国化工园区网最新统计，全国经认定的化工园区中，已有87%建立了集中污水处理设施，76%建有危废处置中心。环保基础设施投资在园区总投资中的占比从2020年的8%提升至2025年的15%。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 1)),
            NewsItem(title="江苏某化工园区污水处理厂提标改造完成，COD排放降至10mg/L以下", source="江苏生态环境", category="工程案例",
                     summary="该园区污水处理厂采用高级氧化+膜生物反应器组合工艺，出水水质达到地表水IV类标准。",
                     content="江苏某国家级化工园区污水处理厂提标改造工程近日完工验收。改造后出水COD稳定控制在10mg/L以下，氨氮控制在0.5mg/L以下，达到《地表水环境质量标准》IV类标准，实现了园区废水近零排放。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 20)),
            NewsItem(title="山东化工园区：VOCs综合治理项目覆盖率达95%", source="山东生态环境", category="行业动态",
                     summary="山东省化工园区挥发性有机物综合治理工程完成，VOCs排放强度下降40%。",
                     content="山东省生态环境厅通报，全省化工园区VOCs综合治理项目已全部完成，重点园区VOCs排放强度较2020年下降40%。园区异味投诉量同比下降60%，园区空气质量明显改善。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 4, 10)),
            NewsItem(title="新版制药工业水污染物排放标准修订启动，预计2026年实施", source="中国医药报", category="政策解读",
                     summary="生态环境部启动制药工业水污染物排放标准修订工作，拟加严抗生素类、激素类制药排放限值。",
                     content="生态环境部近日发布公告，启动《制药工业水污染物排放标准》修订工作。新版标准拟对抗生素类、激素类、抗肿瘤类制药工业的COD、氨氮、特征污染物排放限值进行加严，并新增对新型药物残留物的控制要求。预计2026年上半年正式实施。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 5)),
            NewsItem(title="我国生物医药产业绿色转型：零排放技术成为行业新趋势", source="环保产业网", category="行业动态",
                     summary="绿色制药技术推广加速，连续流反应、酶催化等清洁生产工艺广泛应用。",
                     content="近年来，我国生物医药产业加快绿色转型步伐。连续流反应技术、酶催化技术、微波合成等清洁生产工艺在制药企业广泛应用，废水产生量平均降低60%，VOCs排放降低70%。据行业协会统计，采用绿色工艺的企业废水处理成本降低40%以上。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 20)),
            NewsItem(title="浙江某药企建成智慧环保管控平台，实现排放实时预警", source="浙江生态环境", category="工程案例",
                     summary="该企业通过物联网+AI技术，建立了覆盖全厂的环保智能监控体系。",
                     content="浙江省某大型制药企业近日建成智慧环保管控平台。平台集成了DCS、在线监测、视频AI分析等多系统数据，实现对废水处理站、废气处理设施、危废仓库的24小时智能监控。当监测数据异常时，系统可在5分钟内自动报警并推送处置建议。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 15)),
            NewsItem(title="医药行业VOCs治理面临挑战，RTO技术升级成热点", source="环保在线", category="技术前沿",
                     summary="制药行业VOCs治理市场年规模超过50亿元，蓄热式热氧化炉成为主流技术。",
                     content="据行业调研，制药行业VOCs治理市场年规模超过50亿元。蓄热式热氧化炉(RTO)因其95%以上的热效率、稳定的净化效果成为主流技术。同时，分子筛浓缩+RTO组合工艺在低浓度大风量废气治理中展现出良好应用前景。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 4, 25)),
            NewsItem(title="半导体行业含氟废水处理技术取得突破，氟化物去除率达99.5%", source="新材料在线", category="技术前沿",
                     summary="中科院研发的新型氟化钙纳米吸附材料可高效去除半导体制造废水中的氟化物。",
                     content="中科院上海微系统所研发的新型氟化钙纳米吸附材料在半导体含氟废水处理中取得重大突破。该材料对氟化物的吸附容量是传统材料的3倍，出水氟化物浓度可稳定控制在5mg/L以下，满足最严格的排放标准。目前已在某半导体园区完成中试验证。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 10)),
            NewsItem(title="新能源电池回收环保标准出台，磷酸铁锂回收率要求不低于95%", source="新能源汽车报", category="政策解读",
                     summary="工信部发布废电池回收利用污染控制技术规范，明确各类电池回收处理环保要求。",
                     content="工信部近日发布《废电池回收利用污染控制技术规范》，对锂离子电池、铅蓄电池、镍氢电池等回收利用过程中的污染物排放提出了明确要求。其中，磷酸铁锂电池中有价金属回收率要求不低于95%，湿法冶炼废水需达到《电池工业污染物排放标准》要求。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 28)),
            NewsItem(title="碳纤维行业环保压力加大，烘干废气治理成关键环节", source="复合材料网", category="行业动态",
                     summary="碳纤维生产过程中的烘干废气含有大量氰化氢和丙烯腈，新型催化氧化技术崭露头角。",
                     content="碳纤维生产过程中的预氧化和碳化环节产生大量含氰化氢、丙烯腈等有毒有害气体的烘干废气，治理难度较高。近年来，催化氧化法、等离子体氧化法等新型治理技术在碳纤维行业得到推广应用，氰化氢去除率可达99%以上。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 30)),
            NewsItem(title="光伏制造业能耗双控政策趋严，清洁生产转型迫在眉睫", source="太阳能学报", category="政策解读",
                     summary="国家发改委发布光伏制造业能耗限额标准，超限额企业将面临限产整改。",
                     content="国家发改委近日发布《光伏制造企业能源消耗限额》国家标准，对多晶硅、硅片、电池片、组件各环节的能耗限额提出了明确要求。标准规定，新建光伏项目单位产品综合能耗必须低于限额标准，现有企业三年内需完成节能改造。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 8)),
            NewsItem(title="锂电池生产废水高盐处理技术进展：蒸发结晶实现水资源回收", source="环保产业", category="技术前沿",
                     summary="某环保企业开发的锂电池生产废水零排放技术，实现了高盐废水的资源化利用。",
                     content="锂电池生产过程中产生的废水含有大量有机物和盐分，传统处理方式难以达标。某环保企业研发的电渗析+蒸发结晶组合工艺，可实现锂电池生产废水的近零排放，回收的工业盐可作为副产品出售，每吨处理成本约80元。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 18)),
            NewsItem(title="风电叶片复合材料废弃物处理难题获解，热解回收碳纤维技术成熟", source="风电资讯", category="行业动态",
                     summary="玻璃纤维和碳纤维复合材料叶片的回收处理技术逐步成熟，资源化利用率已达85%以上。",
                     content="随着首批风电叶片进入退役期，复合材料废弃物的处理成为行业焦点。目前，热解法回收碳纤维技术已趋于成熟，回收碳纤维强度可达新纤维的80%以上，热解油可作为燃料回用。玻璃纤维复合材料则通过粉碎后作为建材原料利用，资源化利用率超过85%。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 8)),
            NewsItem(title="化妆品行业废水特征污染物研究深入，内分泌干扰物成监管重点", source="化妆品观察", category="技术前沿",
                     summary="研究发现化妆品废水中含有的邻苯二甲酸酯、对羟基苯甲酸酯等内分泌干扰物对水环境存在潜在风险。",
                     content="近期研究显示，化妆品生产废水中含有的邻苯二甲酸酯类、对羟基苯甲酸酯类、三氯生等内分泌干扰物，即使低浓度也可能对水生生物产生生态毒性。生态环境部正在研究将这些特征污染物纳入化妆品行业废水监管指标。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 25)),
            NewsItem(title="广东化妆品产业园建设集中污水站，处理成本下降30%", source="广东生态环境", category="工程案例",
                     summary="某化妆品产业园集中污水处理厂采用分级治理模式，实现园区废水统一达标排放。",
                     content="广东省某化妆品产业园新建集中污水处理厂，采用企业预处理+园区深度处理的分级治理模式。园区污水处理厂处理规模5000吨/日，出水达到《城市污水再生利用 工业用水水质》标准，处理成本较各企业单独建设降低30%。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 12)),
            NewsItem(title="复合材料行业VOCs排放治理方案讨论会在京召开", source="环保技术", category="行业动态",
                     summary="会议就复合材料树脂基体固化过程中的VOCs排放控制提出了技术路线建议。",
                     content="中国环境保护产业协会复合材料分会近日在京召开VOCs排放治理技术研讨会。会议认为，复合材料制品生产过程中树脂固化环节是VOCs排放的主要来源，建议采用催化燃烧、蓄热燃烧等热力氧化技术进行处理，净化效率可达95%以上。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 4, 18)),
            NewsItem(title="生态环境部：2025年重点行业挥发性有机物综合治理行动方案发布", source="生态环境部", category="政策解读",
                     summary="方案明确石化、化工、工业涂装、包装印刷等重点行业VOCs治理要求。",
                     content="生态环境部近日印发《2025年重点行业挥发性有机物综合治理行动方案》。方案明确，到2027年，全国VOCs排放总量较2020年下降10%以上。重点推进石化、化工、工业涂装、包装印刷、电子制造等行业VOCs源头替代和末端治理。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 1)),
            NewsItem(title="全国碳排放权交易市场扩围，钢铁水泥化工行业纳入在即", source="经济日报", category="政策解读",
                     summary="生态环境部表示，拟于2025年底前将钢铁、水泥、化工等行业纳入全国碳排放权交易市场。",
                     content="生态环境部副部长近日表示，全国碳排放权交易市场正在稳步推进扩围工作。钢铁、水泥、化工等行业已启动碳排放数据核查和配额分配方案编制工作，预计2025年底前正式纳入全国碳市场。此举将有效推动上述高耗能行业绿色低碳转型。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 12)),
            NewsItem(title="新污染物治理行动方案全面实施，内分泌干扰物纳入重点管控名单", source="中国环境报", category="政策解读",
                     summary="生态环境部发布新污染物治理行动方案，明确到2025年完成新污染物调查监测。",
                     content="生态环境部近日发布《新污染物治理行动方案》，明确对全氟化合物、多氯联苯、内分泌干扰物等优先控制新污染物实施源头禁限、过程减排、末端治理全链条管控。方案提出，到2025年完成新污染物调查监测，到2030年建成完善的新污染物治理体系。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 22)),
            NewsItem(title="危险废物焚烧处置能力缺口仍存，专业处置企业加速扩产", source="固废处理", category="行业动态",
                     summary="2025年化工、医药行业危废产生量持续增长，现有处置能力趋紧。",
                     content="据《中国危险废物处置行业年度报告》显示，2024年全国危险废物产生量约1.1亿吨，同比增长8%。其中化工、医药行业危废产量占比超过40%。受处置设施环评审批趋严影响，新增处置能力有限，部分省份出现危废处置能力不足的情况。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 4, 30)),
            NewsItem(title="工业园区废水零直排改造推进，15个试点园区成效明显", source="水利部", category="工程案例",
                     summary="生态环境部遴选的15个工业园区废水零直排试点建设成效显著。",
                     content="生态环境部推进的工业园区废水零直排试点建设工作取得阶段性成果。15个试点园区中，工业废水内部回用率平均达92%，园区集中污水处理厂出水水质普遍达到地表水IV类标准。试点经验将在全国工业园区推广。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 5)),
            NewsItem(title="长江经济带化工企业搬迁改造进展：已搬迁关闭1200余家", source="长江保护", category="行业动态",
                     summary="长江经济带共抓大保护行动深入推进，沿江1公里范围内化工企业已全部关停或搬迁。",
                     content="长江生态环境保护修复联合研究中心发布最新数据：长江经济带沿江1公里范围内已搬迁关闭化工企业1236家，拆除生产设施1800余套。沿江化工园区已完成100%规范化建设，主要入江排污口监测数据全面达标。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 5)),
            NewsItem(title="PM2.5与臭氧协同控制成效显现，重点城市空气质量持续改善", source="中国气象局", category="行业动态",
                     summary="2025年上半年全国PM2.5平均浓度同比下降4.2%，臭氧浓度首次出现同比下降。",
                     content="生态环境部通报，2025年上半年全国PM2.5平均浓度为28μg/m3，同比下降4.2%；臭氧浓度同比下降1.8%，这是臭氧浓度首次出现同比下降。重点原因是石化、化工行业VOCs治理成效显著，重点区域无组织排放管控加强。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 12)),
            NewsItem(title="钢铁焦化行业超低排放改造进入收官阶段，改造完成率超90%", source="冶金环保", category="行业动态",
                     summary="生态环境部表示，钢铁、焦化行业超低排放改造已进入最后攻坚阶段。",
                     content="生态环境部近日通报，全国钢铁企业超低排放改造进展顺利，已完成改造企业超过90%。焦化行业超低排放改造完成率约85%。改造后，重点企业颗粒物、SO2、NOx排放浓度分别降至10mg/m3、35mg/m3、50mg/m3以下。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 30)),
            NewsItem(title="受污染耕地安全利用率达91%，土壤修复产业规模突破200亿", source="生态环境报", category="行业动态",
                     summary="自然资源部数据显示，全国受污染耕地安全利用率稳定在91%以上。",
                     content="自然资源部发布《全国土壤污染防治状况公报》显示，2024年全国受污染耕地安全利用率达91.5%，污染地块安全利用率达92.3%。我国土壤修复产业市场规模预计2025年突破200亿元，主要应用于化工企业搬迁地块、工业园区土壤修复等领域。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 28)),
            NewsItem(title="职业病危害因素检测新规出台，化工企业需每季度开展一次检测", source="职业健康", category="政策解读",
                     summary="国家卫健委发布工作场所职业病危害因素定期检测管理办法。",
                     content="国家卫健委近日发布《工作场所职业病危害因素定期检测管理办法》，要求存在有毒有害物质作业岗位的企业每季度至少开展一次职业病危害因素检测。化工、农药、医药等行业为重点监管对象，检测结果需向当地卫健部门备案并向劳动者公示。",
                     url="https://www.nhc.gov.cn/", published_at=datetime(2025, 6, 8)),
            NewsItem(title="MVR蒸发结晶技术在手算行业应用广泛，能耗降低50%", source="环保技术", category="技术前沿",
                     summary="机械蒸汽再压缩蒸发结晶技术在化工高盐废水处理中得到广泛应用。",
                     content="机械蒸汽再压缩(MVR)蒸发结晶技术在化工、制药等高盐废水处理领域得到越来越广泛的应用。与传统多效蒸发相比，MVR技术将二次蒸汽压缩升温后作为热源循环使用，吨水能耗可降至30-40kWh，较传统工艺降低50%以上，投资回收期一般不超过3年。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 4, 8)),
            NewsItem(title="电化学氧化技术治理难降解有机废水成效显著，COD去除率超95%", source="化工环保", category="技术前沿",
                     summary="硼掺杂金刚石电极电催化氧化技术在处理化工制药高浓度有机废水中展现出优异效果。",
                     content="硼掺杂金刚石(BDD)电极电催化氧化技术在处理化工、制药等高浓度难降解有机废水方面取得显著成效。试验表明，该技术在处理COD 3000-8000mg/L的化工废水时，COD去除率可达95%以上，出水可达排放标准。目前该技术已在江苏、浙江等地多家化工企业推广应用。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 3, 22)),
            NewsItem(title="万华化学环保投资超50亿元，建成国家级绿色工厂", source="化工新闻", category="工程案例",
                     summary="万华化学集团股份有限公司累计环保投入超过50亿元，建成国家级绿色工厂。",
                     content="万华化学集团股份有限公司近年来累计投入环保资金超过50亿元，建成覆盖全厂的废水、废气、固废智能化监控平台。公司烟台基地、宁波基地均获评国家级绿色工厂，主要污染物排放指标优于国家标准50%以上，实现了经济效益与环保效益的双赢。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 22)),
            NewsItem(title="恒力石化循环经济产业园实现固废100%资源化利用", source="石化新闻", category="工程案例",
                     summary="恒力石化产业园通过产业链耦合，实现了副产物的100%资源化利用。",
                     content="恒力石化(大连)产业园通过产业链耦合和循环经济模式，实现了园区内副产物的100%资源化利用。产业园内的炼油-乙烯-芳烃一体化装置产生的废渣、废液全部作为下游装置的原料，废水经深度处理后回用率超过95%，被评为国家级绿色工业园区。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 5, 25)),
            NewsItem(title="欧盟碳边境调节机制CBAM正式实施，化工行业首当其冲", source="国际环保", category="政策解读",
                     summary="欧盟碳边境调节机制于2026年1月1日正式实施，钢铁水泥化工等行业首当其冲。",
                     content="欧盟碳边境调节机制(CBAM)于2026年1月1日正式实施，首批覆盖钢铁、水泥、铝、化肥、电力、氢能六个行业。中国化工企业出口欧盟的产品将需要购买CBAM证书，成本增加约5-15%。企业需加快低碳转型步伐，降低产品碳足迹。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 7, 15)),
            NewsItem(title="全球化学品统一分类和标签制度GHS修订最新进展", source="国际化工", category="政策解读",
                     summary="联合国GHS委员会第七次修订版新增内分泌干扰物分类要求，预计2026年全面生效。",
                     content="联合国《全球化学品分类和标签制度》(GHS)第七次修订版已于2024年发布，新增了对内分泌干扰物、发育毒性、生殖毒性的分类要求。修订版将于2026年1月1日起在全球范围内生效，各国需在2025年底前完成国内法规的转换工作。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 6, 28)),
            NewsItem(title="航空复合材料回收再利用技术获突破，热解法资源化率达90%", source="航空材料", category="技术前沿",
                     summary="某航空材料企业研发的热解回收工艺，可实现碳纤维复合材料制品的高效资源化利用。",
                     content="某航空材料企业研发的新型热解回收工艺，可在600℃以下将碳纤维复合材料制品分解为碳纤维和热解油，碳纤维回收强度保留率超过85%，热解油可回用于热解炉供热，资源化率达90%以上。该技术已获得多项国家专利。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 3, 28)),
            NewsItem(title="土壤修复技术加速迭代，微生物修复在化工地块应用成效显著", source="环境科学", category="技术前沿",
                     summary="微生物修复技术在化工地块土壤修复中展现出良好效果，成本仅为传统方法的30%。",
                     content="近年来，微生物修复技术在化工地块土壤修复中的应用取得显著进展。通过驯化筛选高效降解菌群，可实现对石油烃、多环芳烃、氯代有机物等污染物的有效降解，修复周期较传统方法缩短50%以上，成本降低约70%。",
                     url="https://www.mee.gov.cn/", published_at=datetime(2025, 4, 15)),
        ]

        total_added = 0
        for item in news_items:
            existing = db.query(NewsItem).filter(NewsItem.title == item.title).first()
            if not existing:
                db.add(item)
                total_added += 1
        db.commit()
        print(f"News: Added {total_added} items (total: {db.query(NewsItem).count()})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_news_batch()
