"""
Agent 工具链 — 所有可被 Agent 调用的工具函数
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import re
from datetime import datetime, timedelta

from app.db.models import (
    Standard, PollutionFactor, PollutionLimit, Device, DeviceReading,
    NewsItem, ReportTemplate, ReportInstance, EnterpriseStandard, CrawlLog
)


class Tools:
    """Agent 的工具集合"""

    def __init__(self, db: Session):
        self.db = db

    # ──────────────────────────────────────────
    #  知识检索工具
    # ──────────────────────────────────────────

    async def search_standards(self, query: str) -> Dict[str, Any]:
        """搜索环保标准"""
        kw = query.lower()
        results = {
            "standards": [],
            "factors": [],
            "limits": [],
        }

        # 标准全文搜索
        standards = self.db.query(Standard).filter(
            Standard.title.contains(kw) |
            Standard.content.contains(kw)
        ).limit(20).all()
        for s in standards:
            results["standards"].append({
                "id": s.id,
                "title": s.title,
                "type": s.standard_type,
                "industry": s.industry,
                "publish_date": str(s.publish_date)[:10],
                "summary": s.content[:200] if s.content else "",
            })

        # 因子匹配
        factors = self.db.query(PollutionFactor).all()
        matched_factors = []
        for f in factors:
            if f.name in kw or f.symbol.lower() in kw:
                limits = self.db.query(PollutionLimit).filter(
                    PollutionLimit.factor_id == f.id
                ).all()
                matched_factors.append({
                    "id": f.id,
                    "name": f.name,
                    "symbol": f.symbol,
                    "unit": f.unit,
                    "limits": [
                        {
                            "standard": l.standard_title,
                            "value": l.limit_value,
                            "type": l.standard_type,
                            "desc": l.description,
                        }
                        for l in limits
                    ],
                })
        results["factors"] = matched_factors
        results["limits"] = [
            {
                "factor": f["name"],
                "standard": l["standard"],
                "value": l["value"],
                "type": l["type"],
            }
            for f in matched_factors
            for l in f["limits"]
        ]
        return results

    async def get_factor_limits(self, factor_name: str) -> Dict[str, Any]:
        """获取特定污染因子的全部限值"""
        factor = self.db.query(PollutionFactor).filter(
            PollutionFactor.name.contains(factor_name) |
            PollutionFactor.symbol.contains(factor_name)
        ).first()
        if not factor:
            return {"error": f"未找到因子: {factor_name}"}
        limits = self.db.query(PollutionLimit).filter(
            PollutionLimit.factor_id == factor.id
        ).all()
        return {
            "factor": factor.name,
            "symbol": factor.symbol,
            "unit": factor.unit,
            "limits": [
                {
                    "standard": l.standard_title,
                    "value": l.limit_value,
                    "type": l.standard_type,
                    "description": l.description,
                }
                for l in limits
            ],
        }

    async def compare_standards(self, standard_ids: List[int]) -> Dict[str, Any]:
        """对比多个标准的差异"""
        standards = self.db.query(Standard).filter(
            Standard.id.in_(standard_ids)
        ).all()
        result = []
        for s in standards:
            result.append({
                "id": s.id,
                "title": s.title,
                "type": s.standard_type,
                "industry": s.industry,
                "pollution_factors": s.pollution_factors,
                "publish_date": str(s.publish_date)[:10],
                "content": s.content,
            })
        return {"standards": result}

    # ──────────────────────────────────────────
    #  数据分析工具
    # ──────────────────────────────────────────

    async def analyze_device(self, device_id: int) -> Dict[str, Any]:
        """分析设备数据，检测异常，预测趋势"""
        device = self.db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": "设备不存在"}

        since = datetime.now() - timedelta(hours=24)
        readings = self.db.query(DeviceReading).filter(
            DeviceReading.device_id == device_id,
            DeviceReading.timestamp >= since,
        ).order_by(DeviceReading.timestamp).all()

        if not readings:
            return {"device_id": device_id, "message": "暂无数据", "device": device.name}

        values = [r.value for r in readings]
        n = len(values)
        avg = sum(values) / n
        max_val = max(values)
        min_val = min(values)
        exceed_count = sum(1 for r in readings if r.status == "exceed")

        # 趋势分析
        recent = values[-12:] if n >= 12 else values
        older = values[:-12] if n > 12 else []
        if older and len(older) >= 6:
            older_avg = sum(older) / len(older)
            recent_avg = sum(recent) / len(recent)
            trend = "上升" if recent_avg > older_avg * 1.1 else \
                    "下降" if recent_avg < older_avg * 0.9 else "稳定"
        else:
            trend = "数据不足"

        # 异常检测（简单统计方法）
        anomalies = []
        if n >= 6:
            std_dev = (sum((v - avg) ** 2 for v in values) / n) ** 0.5
            threshold = avg + 2 * std_dev if std_dev > 0 else avg * 1.5
            for i, r in enumerate(readings):
                if r.value > threshold:
                    anomalies.append({
                        "time": str(r.timestamp),
                        "value": r.value,
                        "threshold": round(threshold, 2),
                    })

        # 限值对比 — 通过 PollutionFactor 表匹配 symbol
        factor_obj = self.db.query(PollutionFactor).filter(
            PollutionFactor.symbol == device.factor
        ).first()
        limits = []
        if factor_obj:
            limits = self.db.query(PollutionLimit).filter(
                PollutionLimit.factor_id == factor_obj.id
            ).all()
        current_limit = limits[0].limit_value if limits else None

        # AI 建议
        suggestions = []
        if current_limit and max_val > current_limit:
            suggestions.append(f"⚠️ 最大值 {max_val:.2f}{device.unit} 已超过限值 {current_limit}{device.unit}，需立即处理")
        if trend == "上升":
            suggestions.append("📈 近期排放呈上升趋势，建议检查治理设施运行状态")
        if exceed_count > 0:
            suggestions.append(f"📊 过去24小时有 {exceed_count} 次超标记录，建议排查原因")
        if not suggestions:
            suggestions.append("✅ 排放数据正常，建议继续保持现有运维模式")

        # 简单预测（移动平均）
        if n >= 6:
            predicted = sum(values[-6:]) / 6
            prediction = f"预测未来排放均值约 {predicted:.2f}{device.unit}"
        else:
            prediction = "数据量不足，无法预测"

        return {
            "device_id": device_id,
            "device_name": device.name,
            "factor": device.factor,
            "unit": device.unit,
            "statistics": {
                "avg": round(avg, 2),
                "max": round(max_val, 2),
                "min": round(min_val, 2),
                "recent_avg": round(sum(recent) / len(recent), 2) if recent else None,
                "trend": trend,
                "total_readings": n,
                "exceed_count": exceed_count,
            },
            "limit": current_limit,
            "anomalies": anomalies[:5],
            "suggestions": suggestions,
            "prediction": prediction,
            "data_points": [
                {"timestamp": str(r.timestamp), "value": r.value, "status": r.status}
                for r in readings[-50:]
            ],
        }

    async def check_exceedances(self, hours: int = 24) -> Dict[str, Any]:
        """检查超标记录"""
        since = datetime.now() - timedelta(hours=hours)
        readings = self.db.query(DeviceReading).filter(
            DeviceReading.timestamp >= since,
            DeviceReading.status == "exceed",
        ).all()

        if not readings:
            return {"message": f"过去{hours}小时内无超标记录", "count": 0}

        results = []
        for r in readings:
            device = self.db.query(Device).filter(Device.id == r.device_id).first()
            results.append({
                "device": device.name if device else f"设备#{r.device_id}",
                "factor": r.factor,
                "value": r.value,
                "unit": r.unit,
                "time": str(r.timestamp),
            })

        return {"count": len(results), "records": results}

    # ──────────────────────────────────────────
    #  报告生成工具
    # ──────────────────────────────────────────

    async def generate_report(self, template_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """根据模板类型生成报告"""
        from app.routers.reports import (
            _generate_daily_inspection,
            _generate_exceed_analysis,
            _generate_compliance_check,
            _generate_annual_report,
        )

        gen_map = {
            "daily_inspection": _generate_daily_inspection,
            "exceed_analysis": _generate_exceed_analysis,
            "compliance_check": _generate_compliance_check,
            "annual_report": _generate_annual_report,
        }

        func = gen_map.get(template_type)
        if not func:
            return {"error": f"不支持的报告类型: {template_type}"}

        # 查找模板
        template = self.db.query(ReportTemplate).filter(
            ReportTemplate.type == template_type
        ).first()
        if not template:
            return {"error": "模板不存在，请先运行 /api/reports/seed"}

        content = func(template, params, self.db)

        instance = ReportInstance(
            template_id=template.id,
            params=params,
            content=content,
            status="generated",
            generated_at=datetime.now(),
        )
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        return {
            "id": instance.id,
            "template": template_type,
            "content": content,
            "status": "generated",
        }

    # ──────────────────────────────────────────
    #  新闻与信息工具
    # ──────────────────────────────────────────

    async def search_news(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索新闻"""
        news = self.db.query(NewsItem).filter(
            NewsItem.title.contains(keyword) |
            NewsItem.summary.contains(keyword)
        ).order_by(NewsItem.published_at.desc()).limit(limit).all()
        return [
            {
                "id": n.id,
                "title": n.title,
                "source": n.source,
                "published_at": str(n.published_at),
                "tags": n.tags,
                "url": n.url,
            }
            for n in news
        ]

    # ──────────────────────────────────────────
    #  网络爬虫工具
    # ──────────────────────────────────────────

    async def crawl_andingest_standards(
        self,
        source: str = "auto",
        limit: int = 20,
    ) -> Dict[str, Any]:
        results = {
            "sources_checked": [],
            "new_standards": 0,
            "new_factors": 0,
            "new_limits": 0,
            "errors": [],
            "details": [],
        }

        # 定义爬取任务
        crawl_tasks = []

        if source in ("auto", "mee"):
            crawl_tasks.append({
                "name": "生态环境部-最新标准",
                "url": "https://www.mee.gov.cn/ywgz/guid-fz/gdfdpgz/bzlb/",
                "parser": self._parse_mee_standards,
            })

        if source in ("auto", "std"):
            crawl_tasks.append({
                "name": "国家标准全文公开",
                "url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=20240115-C32-0001",
                "parser": self._parse_gb_standards,
            })

        # 已知的环保标准URL（定期更新）
        known_urls = [
            ("GB 16297-1996 大气污染物综合排放标准",
             "https://www.mee.gov.cn/ywgz/guidfz/gdfdpgz/bzlb/201905/t20190507_499939.shtml"),
            ("GB 8978-1996 污水综合排放标准",
             "https://www.mee.gov.cn/ywgz/guidfz/gdfdpgz/bzlb/201905/t20190507_499941.shtml"),
            ("GB 31570-2015 石油化学工业污染物排放标准",
             "https://www.mee.gov.cn/ywgz/guidfz/gdfdpgz/bzlb/201708/P020170811585155108696.pdf"),
        ]

        new_count = 0
        limit_reached = False

        for task in crawl_tasks[:3]:  # 限制爬取数量
            try:
                detail = await self._crawl_single(task["url"], task["name"], task["parser"])
                results["sources_checked"].append(task["name"])
                if detail.get("added"):
                    new_count += detail["added"]
                    results["details"].append(detail)
                    if new_count >= limit:
                        limit_reached = True
                        break
            except Exception as e:
                results["errors"].append(f"{task['name']}: {str(e)[:100]}")

        # 处理已知URL
        if not limit_reached:
            for title, url in known_urls:
                if new_count >= limit:
                    break
                try:
                    detail = await self._crawl_single(url, title, self._parse_standard_page)
                    results["sources_checked"].append(title[:30])
                    if detail.get("added"):
                        new_count += detail["added"]
                        results["details"].append(detail)
                except Exception as e:
                    results["errors"].append(f"{title[:30]}: {str(e)[:80]}")

        results["new_standards"] = new_count
        return results

    async def _crawl_single(
        self, url: str, source_name: str, parser_fn
    ) -> Dict[str, Any]:
        """爬取单个页面"""
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
            except Exception as e:
                return {"url": url, "error": str(e), "added": 0}

            parsed = parser_fn(resp.text, url)

            # 入库
            added = 0
            for std_data in parsed:
                existing = self.db.query(Standard).filter(
                    Standard.title == std_data["title"]
                ).first()
                if not existing:
                    std = Standard(
                        title=std_data["title"],
                        standard_type=std_data.get("type", "unknown"),
                        industry=std_data.get("industry", "general"),
                        pollution_factors=std_data.get("factors", []),
                        publish_date=datetime.strptime(std_data.get("date", "2020-01-01"), "%Y-%m-%d") if std_data.get("date") else datetime.now(),
                        content=std_data.get("content", ""),
                        source_url=std_data.get("url", url),
                    )
                    self.db.add(std)
                    self.db.flush()

                    # 添加限值
                    for lim in std_data.get("limits", []):
                        limit_obj = PollutionLimit(
                            factor_id=lim.get("factor_id"),
                            standard_title=std_data["title"],
                            limit_value=lim.get("value"),
                            unit=lim.get("unit", "mg/m³"),
                            standard_type=std_data.get("type", "unknown"),
                            description=lim.get("desc", ""),
                        )
                        self.db.add(limit_obj)
                    added += 1

            # 记录爬取日志
            log = CrawlLog(
                source=source_name,
                url=url,
                title=parsed[0]["title"] if parsed else source_name,
                new_standards=added,
                status="success" if added > 0 else "no_new",
                crawled_at=datetime.now(),
            )
            self.db.add(log)
            self.db.commit()

            return {"url": url, "added": added, "parsed_count": len(parsed)}

    def _parse_mee_standards(self, html: str, url: str) -> List[Dict]:
        """解析生态环境部标准页面（纯正则，无需BeautifulSoup）"""
        import re
        standards = []
        # 匹配链接中的标准名称
        link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        for match in re.finditer(link_pattern, html):
            href, text = match.groups()
            text = text.strip()
            if any(kw in text for kw in ["标准", "排放标准", "GB", "HJ"]):
                standards.append({
                    "title": text,
                    "type": self._classify_standard(text),
                    "factors": self._extract_factors(text),
                    "url": href if href.startswith("http") else url + "/" + href,
                    "content": f"来自生态环境部官网: {text}",
                })
        return standards[:5]

    def _parse_gb_standards(self, html: str, url: str) -> List[Dict]:
        """解析国标页面"""
        import re
        standards = []
        # 匹配表格行中的标准
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        for match in re.finditer(row_pattern, html, re.DOTALL):
            row = match.group(1)
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            texts = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            if texts and any("GB" in t for t in texts):
                standards.append({
                    "title": texts[0] if texts else "",
                    "type": "national",
                    "factors": [],
                    "url": url,
                    "content": " | ".join(texts[:3]),
                })
        return standards[:10]

    def _parse_standard_page(self, soup, url) -> List[Dict]:
        """通用标准页面解析"""
        text = soup.get_text()
        title_match = re.search(r"([\u4e00-\u9fa5]+(?:标准|规范|规程|规定))", text[:500])
        title = title_match.group(1) if title_match else url.split("/")[-1][:50]

        # 尝试提取限值信息
        limits = []
        for match in re.finditer(r"(\d+)\s*([mgLμg/m³]+)\s*(?:≤|>=|限值|标准值)", text):
            limits.append({"value": float(match.group(1)), "unit": match.group(2)})

        return [{
            "title": title,
            "type": "national",
            "factors": self._extract_factors(title),
            "url": url,
            "content": text[:2000],
            "limits": limits[:5],
        }]

    def _classify_standard(self, title: str) -> str:
        """根据标题分类标准类型"""
        if "GB" in title:
            return "national"
        if "HJ" in title or "行标" in title:
            return "industry"
        if "DB" in title:
            return "local"
        if "ISO" in title or "IEC" in title:
            return "international"
        return "unknown"

    def _extract_factors(self, text: str) -> List[str]:
        """从标题/内容中提取污染因子"""
        factor_keywords = [
            ("VOCs", "VOCs"), ("挥发性有机物", "VOCs"),
            ("COD", "COD"), ("化学需氧量", "COD"),
            ("氨氮", "NH₃-N"), ("NH₃-N", "NH₃-N"),
            ("SO₂", "SO₂"), ("二氧化硫", "SO₂"),
            ("NOx", "NOx"), ("氮氧化物", "NOx"),
            ("PM", "PM"), ("颗粒物", "PM"),
            ("Hg", "Hg"), ("总汞", "Hg"),
        ]
        factors = []
        for kw, sym in factor_keywords:
            if kw in text and sym not in factors:
                factors.append(sym)
        return factors

    # ──────────────────────────────────────────
    #  数据上传处理工具
    # ──────────────────────────────────────────

    async def process_uploaded_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """处理用户上传的数据文件（CSV/JSON）"""
        file_content = payload.get("content", "")
        filename = payload.get("filename", "upload")
        file_format = payload.get("format", "auto")

        # 解析数据
        try:
            if file_format == "auto":
                file_format = "csv" if "." in filename and filename.rsplit(".", 1)[-1] == "csv" else "json"

            if file_format == "csv":
                import io
                lines = file_content.strip().split("\n")
                headers = lines[0].split(",") if lines else []
                rows = []
                for line in lines[1:]:
                    rows.append(dict(zip(headers, line.split(","))))
            else:
                rows = json.loads(file_content)
                headers = list(rows[0].keys()) if rows else []

            # 自动识别设备/因子
            device_name = payload.get("device_name", filename.replace(".", "_"))
            factor_name = payload.get("factor", "VOCs")
            unit = payload.get("unit", "mg/m³")

            # 保存为设备读数
            created = 0
            for row in rows[:1000]:  # 限制条数
                try:
                    reading = DeviceReading(
                        device_id=-1,  # 待分配
                        factor=factor_name,
                        value=float(row.get("value", row.get("concentration", 0))),
                        unit=unit,
                        timestamp=datetime.fromisoformat(row.get("timestamp", row.get("time", datetime.now().isoformat()))),
                        status=row.get("status", "normal"),
                    )
                    self.db.add(reading)
                    created += 1
                except (ValueError, TypeError):
                    continue

            self.db.commit()

            # 语义记忆存储
            from app.memory import MemoryManager
            mem = MemoryManager(self.db)
            mem.save_semantic(
                session_id="upload",
                text=f"上传了{created}条{factor_name}监测数据，文件: {filename}",
                metadata={"source": "data_upload", "count": created, "factor": factor_name},
            )

            return {
                "status": "success",
                "created": created,
                "headers": headers,
                "sample": rows[:3],
                "message": f"成功导入 {created} 条数据",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ──────────────────────────────────────────
    #  搜索引擎工具
    # ──────────────────────────────────────────

    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """网络搜索 — 调用 AnySearch / Tavily 获取最新环保资讯"""
        from app.search_engine import SearchEngine
        engine = SearchEngine()
        return await engine.search(query, max_results)

    # ──────────────────────────────────────────
    #  综合知识检索
    # ──────────────────────────────────────────

    async def search_knowledge(self, query: str) -> Dict[str, Any]:
        """综合知识检索（聚合多个数据源）"""
        return {
            "standards": await self.search_standards(query),
            "news": await self.search_news(query, limit=5),
            "regulation": await self.search_regulation(query),
        }

    async def search_regulation(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """搜索公约/法规条款"""
        kw = query.lower()
        from app.db.models import RegulationClause
        clauses = self.db.query(RegulationClause).filter(
            (RegulationClause.content.contains(query)) |
            (RegulationClause.article_title.contains(query)) |
            (RegulationClause.source.contains(query))
        ).limit(top_k).all()

        results = []
        for c in clauses:
            score = 0
            if c.article_title and query in c.article_title:
                score += 10
            if c.content and query in c.content:
                score += 5
            if c.keywords and any(kw in k.lower() for k in c.keywords):
                score += 3
            results.append({
                "id": c.id,
                "source": c.source,
                "chapter": c.chapter,
                "article_no": c.article_no,
                "article_title": c.article_title,
                "content": c.content,
                "keywords": c.keywords or [],
                "action_required": c.action_required,
                "platform_url": c.platform_url,
                "score": score,
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return {"query": query, "count": len(results), "clauses": results[:top_k]}

    async def get_all_limits_for_factor(self, factor_symbol: str) -> List[Dict]:
        """获取某因子的所有限值（用于报告生成时引用）"""
        factor = self.db.query(PollutionFactor).filter(
            PollutionFactor.symbol == factor_symbol
        ).first()
        if not factor:
            return []
        limits = self.db.query(PollutionLimit).filter(
            PollutionLimit.factor_id == factor.id
        ).all()
        return [
            {
                "standard": l.standard_title,
                "value": l.limit_value,
                "type": l.standard_type,
                "desc": l.description,
            }
            for l in limits
        ]
