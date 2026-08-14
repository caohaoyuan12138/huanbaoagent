<template>
  <div class="reports-page">
    <el-row :gutter="16" style="height: 100%">
      <!-- 左侧：报告模板列表 -->
      <el-col :span="7">
        <div class="card" style="height: 100%; display: flex; flex-direction: column;">
          <div class="card-header">
            <h3>报告模板</h3>
          </div>
          <div class="card-body" style="padding: 0; flex: 1; overflow-y: auto">
            <div
              v-for="tpl in templates"
              :key="tpl.id"
              class="tpl-item"
              :class="{ active: selectedTemplate?.id === tpl.id }"
              @click="selectTemplate(tpl)"
            >
              <div style="display: flex; align-items: center; gap: 10px">
                <el-icon :size="20" style="color: #4ade80; flex-shrink: 0">
                  <component :is="tplIcon(tpl.type)" />
                </el-icon>
                <div>
                  <div style="font-size: 14px; font-weight: 500">{{ tpl.name }}</div>
                  <div style="font-size: 12px; color: #999; margin-top: 2px">{{ tpl.description }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 右侧：报告生成/预览 -->
      <el-col :span="17">
        <div class="card" style="height: 100%; display: flex; flex-direction: column;">
          <div class="card-header">
            <h3>{{ selectedTemplate?.name || '请选择报告模板' }}</h3>
            <div style="display: flex; gap: 8px" v-if="selectedTemplate">
              <el-button size="small" @click="generateReport" :loading="generating">
                <el-icon><Promotion /></el-icon> 生成报告
              </el-button>
              <el-button v-if="currentReport" size="small" type="success" @click="exportReport">
                <el-icon><Download /></el-icon> 导出
              </el-button>
            </div>
          </div>
          <div class="card-body" style="flex: 1; overflow-y: auto" v-if="selectedTemplate">
            <!-- 参数填写 -->
            <el-form :model="reportParams" label-width="120px" v-if="!currentReport">
              <el-form-item label="报告日期" v-if="selectedTemplate.fields.includes('date')">
                <el-date-picker v-model="reportParams.date" type="date" value-format="YYYY-MM-DD" style="width: 200px" />
              </el-form-item>
              <el-form-item label="报告编号" v-if="selectedTemplate.fields.includes('report_no')">
                <el-input v-model="reportParams.report_no" style="width: 250px" />
              </el-form-item>
              <el-form-item label="车间名称" v-if="selectedTemplate.fields.includes('workshop')">
                <el-input v-model="reportParams.workshop" placeholder="如：一号车间" style="width: 250px" />
              </el-form-item>
              <el-form-item label="巡查人员" v-if="selectedTemplate.fields.includes('inspector')">
                <el-input v-model="reportParams.inspector" placeholder="如：张三" style="width: 250px" />
              </el-form-item>
              <el-form-item label="企业名称" v-if="selectedTemplate.fields.includes('factory_name')">
                <el-input v-model="reportParams.factory_name" placeholder="如：XX化工有限公司" style="width: 300px" />
              </el-form-item>
              <el-form-item label="所属行业" v-if="selectedTemplate.fields.includes('industry')">
                <el-select v-model="reportParams.industry" style="width: 250px">
                  <el-option label="石油化工" value="石油化工" />
                  <el-option label="精细化工" value="精细化工" />
                  <el-option label="制药" value="制药" />
                  <el-option label="农药" value="农药" />
                  <el-option label="煤化工" value="煤化工" />
                  <el-option label="无机化工" value="无机化工" />
                </el-select>
              </el-form-item>
              <el-form-item label="报告年份" v-if="selectedTemplate.fields.includes('year')">
                <el-input-number v-model="reportParams.year" :min="2020" :max="2030" />
              </el-form-item>
              <el-form-item label="污染因子" v-if="selectedTemplate.fields.includes('factor')">
                <el-select v-model="reportParams.factor" style="width: 250px">
                  <el-option v-for="f in pollutionFactors" :key="f.symbol" :label="`${f.name}(${f.symbol})`" :value="f.symbol" />
                </el-select>
              </el-form-item>
              <el-form-item label="排放限值" v-if="selectedTemplate.fields.includes('limit_value')">
                <el-input-number v-model="reportParams.limit_value" :precision="2" style="width: 150px" />
                <span style="margin-left: 8px; color: #999">mg/L</span>
              </el-form-item>
              <el-form-item label="实测值" v-if="selectedTemplate.fields.includes('actual_value')">
                <el-input-number v-model="reportParams.actual_value" :precision="2" style="width: 150px" />
                <span style="margin-left: 8px; color: #999">mg/L</span>
              </el-form-item>
              <el-form-item label="超标倍数" v-if="selectedTemplate.fields.includes('exceed_ratio')">
                <el-input-number v-model="reportParams.exceed_ratio" :precision="2" :step="0.1" :min="1" style="width: 150px" />
              </el-form-item>

              <!-- 设备清单 -->
              <el-form-item label="设备清单" v-if="selectedTemplate.fields.includes('equipment')">
                <div style="width: 100%">
                  <div v-for="(eq, idx) in reportParams.equipment" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center">
                    <el-input v-model="eq.name" placeholder="设备名称" style="width: 200px" />
                    <el-select v-model="eq.status" style="width: 120px">
                      <el-option label="正常" value="正常" />
                      <el-option label="异常" value="异常" />
                    </el-select>
                    <el-input v-model="eq.remark" placeholder="备注（可选）" style="width: 180px" />
                    <el-button size="small" type="danger" circle @click="reportParams.equipment.splice(idx, 1)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" @click="reportParams.equipment.push({ name: '', status: '正常', remark: '' })">
                    <el-icon><Plus /></el-icon> 添加设备
                  </el-button>
                </div>
              </el-form-item>

              <!-- 排放数据 -->
              <el-form-item label="排放数据" v-if="selectedTemplate.fields.includes('emission_data')">
                <div style="width: 100%">
                  <div v-for="(item, idx) in reportParams.emission_data" :key="idx" style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center">
                    <el-input v-model="item.factor" placeholder="因子名称" style="width: 120px" />
                    <el-input-number v-model="item.value" :precision="2" placeholder="数值" style="width: 120px" />
                    <el-input v-model="item.unit" placeholder="单位" style="width: 80px" />
                    <el-select v-model="item.status" style="width: 100px">
                      <el-option label="正常" value="normal" />
                      <el-option label="超标" value="exceed" />
                    </el-select>
                    <el-button size="small" type="danger" circle @click="reportParams.emission_data.splice(idx, 1)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" @click="reportParams.emission_data.push({ factor: '', value: 0, unit: 'mg/L', status: 'normal' })">
                    <el-icon><Plus /></el-icon> 添加数据
                  </el-button>
                </div>
              </el-form-item>

              <!-- 废气排放数据 -->
              <el-form-item label="废气排放数据" v-if="selectedTemplate.fields.includes('exhaust_items')">
                <el-input
                  v-model="reportParams.exhaust_items"
                  type="textarea"
                  :rows="3"
                  placeholder="如：SO₂ 50mg/m³(达标), NOx 80mg/m³(达标), VOCs 30mg/m³(超标)"
                />
              </el-form-item>

              <!-- 废水排放数据 -->
              <el-form-item label="废水排放数据" v-if="selectedTemplate.fields.includes('wastewater_items')">
                <el-input
                  v-model="reportParams.wastewater_items"
                  type="textarea"
                  :rows="3"
                  placeholder="如：COD 45mg/L(达标), NH₃-N 8mg/L(达标), SS 30mg/L(达标)"
                />
              </el-form-item>

              <!-- 存在问题 -->
              <el-form-item label="存在问题" v-if="selectedTemplate.fields.includes('issues')">
                <el-input
                  v-model="reportParams.issues"
                  type="textarea"
                  :rows="3"
                  placeholder="如：1. VOCs治理设施效率下降；2. 废水调节池液位偏高"
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="generateReport" :loading="generating">生成报告</el-button>
              </el-form-item>
            </el-form>

            <!-- 报告预览 -->
            <div v-else class="report-preview" v-html="renderMarkdown(currentReport.content)"></div>
          </div>
          <div v-else class="card-body" style="text-align: center; padding: 60px; color: #999; flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <el-icon :size="48" style="margin-bottom: 12px"><Document /></el-icon>
            <div>请从左侧选择报告模板</div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const templates = ref([])
const reports = ref([])
const pollutionFactors = ref([])
const selectedTemplate = ref(null)
const currentReport = ref(null)
const reportParams = ref({})
const generating = ref(false)

const tplIconMap = {
  daily_inspection: 'Tickets',
  exceed_analysis: 'Warning',
  compliance_check: 'Check',
  annual_report: 'Calendar',
}

const tplIcon = (type) => tplIconMap[type] || 'Document'

const loadTemplates = async () => {
  try {
    templates.value = await api.get('/reports/templates')
  } catch (e) {
    ElMessage.error('加载模板失败')
  }
}

const loadReports = async () => {
  try {
    reports.value = await api.get('/reports/instances')
  } catch (e) {
    console.error('加载报告失败', e)
  }
}

const loadFactors = async () => {
  try {
    pollutionFactors.value = await api.get('/knowledge/pollution-factors')
  } catch (e) {
    console.error('加载因子失败', e)
  }
}

const selectTemplate = (tpl) => {
  selectedTemplate.value = tpl
  currentReport.value = null
  reportParams.value = {
    date: new Date().toISOString().slice(0, 10),
    year: new Date().getFullYear(),
    report_no: 'RB-' + new Date().toISOString().slice(0, 10).replace(/-/g, ''),
    workshop: '一号车间',
    inspector: '',
    factory_name: '',
    industry: '石油化工',
    factor: 'COD',
    limit_value: 50,
    actual_value: 75,
    exceed_ratio: 1.5,
    equipment: [
      { name: 'RTO蓄热焚烧炉', status: '正常', remark: '' },
      { name: '水洗塔', status: '正常', remark: '' },
      { name: '活性炭吸附箱', status: '正常', remark: '' },
      { name: '废水调节池', status: '正常', remark: '' },
      { name: 'COD在线监测仪', status: '正常', remark: '' },
    ],
    emission_data: [
      { factor: 'SO₂', value: 35, unit: 'mg/m³', status: 'normal' },
      { factor: 'NOx', value: 60, unit: 'mg/m³', status: 'normal' },
      { factor: 'VOCs', value: 25, unit: 'mg/m³', status: 'normal' },
    ],
    exhaust_items: 'SO₂ 35mg/m³(达标), NOx 60mg/m³(达标), VOCs 25mg/m³(达标), 颗粒物 15mg/m³(达标)',
    wastewater_items: 'COD 45mg/L(达标), NH₃-N 8mg/L(达标), SS 30mg/L(达标), 石油类 2mg/L(达标)',
    issues: '暂无重大环保问题，建议加强VOCs治理设施维护',
  }
}

const generateReport = async () => {
  if (!selectedTemplate.value) return
  generating.value = true
  try {
    const res = await api.post('/reports/generate', {
      template_id: selectedTemplate.value.id,
      params: reportParams.value,
    })
    currentReport.value = res
    ElMessage.success('报告生成成功')
  } catch (e) {
    ElMessage.error('报告生成失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    generating.value = false
  }
}

const exportReport = () => {
  if (!currentReport.value) return
  const content = currentReport.value.content
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `报告_${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN')
}

const renderMarkdown = (md) => {
  if (!md) return ''
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

onMounted(() => {
  loadTemplates()
  loadFactors()
})
</script>

<style scoped>
.reports-page {
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
}

.tpl-item {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: background 0.2s;
}

.tpl-item:hover {
  background: #f9fafb;
}

.tpl-item.active {
  background: #f0fdf4;
  border-left: 3px solid #22c55e;
  padding-left: 13px;
}
</style>
