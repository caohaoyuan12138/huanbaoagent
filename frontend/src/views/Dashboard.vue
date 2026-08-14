<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">接入设备</div>
          <div class="stat-value" style="color: #4ade80">{{ devices.length }}</div>
          <div class="stat-change">在线运行中</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">知识库标准</div>
          <div class="stat-value" style="color: #60a5fa">{{ standards.length }}</div>
          <div class="stat-change">国标/行标/地标</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">今日资讯</div>
          <div class="stat-value" style="color: #f59e0b">{{ news.length }}</div>
          <div class="stat-change">条最新环保新闻</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">生成报告</div>
          <div class="stat-value" style="color: #a78bfa">{{ reports.length }}</div>
          <div class="stat-change">份历史报告</div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 设备实时监控 -->
      <el-col :span="16">
        <div class="card" style="height: 420px">
          <div class="card-header">
            <h3><el-icon><Monitor /></el-icon> 实时排放监控</h3>
            <el-select v-model="selectedDevice" size="small" style="width: 160px" @change="loadDeviceData">
              <el-option
                v-for="d in devices"
                :key="d.id"
                :label="d.name"
                :value="d.id"
              />
            </el-select>
          </div>
          <div class="card-body">
            <v-chart
              v-if="chartData.length > 0"
              :option="chartOption"
              autoresize
              style="height: 320px"
            />
            <el-empty v-else description="暂无数据，请先接入设备" :image-size="80" />
          </div>
        </div>
      </el-col>

      <!-- 最新异常 -->
      <el-col :span="8">
        <div class="card" style="height: 420px">
          <div class="card-header">
            <h3><el-icon><Warning /></el-icon> 最新异常</h3>
            <el-badge :value="alerts.length" type="danger">
              <el-button size="small" type="primary" plain round>刷新</el-button>
            </el-badge>
          </div>
          <div class="card-body" style="padding: 0">
            <el-timeline v-if="alerts.length > 0" style="padding: 16px">
              <el-timeline-item
                v-for="(alert, idx) in alerts"
                :key="idx"
                :timestamp="alert.time"
                type="danger"
                placement="top"
              >
                <el-card shadow="hover" style="cursor: pointer">
                  <div style="font-size: 13px; font-weight: 500">{{ alert.device }}</div>
                  <div style="font-size: 12px; color: #666; margin-top: 4px">{{ alert.message }}</div>
                </el-card>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无异常" :image-size="60" style="padding: 40px 0" />
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 最新新闻 -->
      <el-col :span="12">
        <div class="card">
          <div class="card-header">
            <h3><el-icon><Bell /></el-icon> 最新环保资讯</h3>
            <router-link to="/news" style="font-size: 13px; color: #4ade80; text-decoration: none">查看更多 →</router-link>
          </div>
          <div class="card-body" style="padding: 0">
            <div
              v-for="item in news.slice(0, 4)"
              :key="item.id"
              style="padding: 12px 16px; border-bottom: 1px solid #f0f0f0; cursor: pointer"
              @click="openNews(item)"
            >
              <div style="font-size: 13px; font-weight: 500; color: #1a1a1a; margin-bottom: 4px">
                {{ item.title }}
              </div>
              <div style="font-size: 11px; color: #999">
                {{ item.source }} · {{ formatDate(item.published_at) }}
              </div>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 知识库快速查询 -->
      <el-col :span="12">
        <div class="card">
          <div class="card-header">
            <h3><el-icon><Search /></el-icon> 排放限值快速查询</h3>
            <router-link to="/knowledge" style="font-size: 13px; color: #4ade80; text-decoration: none">查看全部 →</router-link>
          </div>
          <div class="card-body">
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px">
              <el-tag
                v-for="factor in pollutionFactors"
                :key="factor.id"
                closable
                @close="removeFactor(factor)"
                @click="queryFactor(factor)"
                style="cursor: pointer"
              >
                {{ factor.name }}({{ factor.symbol }})
              </el-tag>
            </div>
            <div v-if="selectedFactor" style="background: #f0fdf4; border-radius: 8px; padding: 12px">
              <div style="font-size: 13px; font-weight: 500; color: #166534; margin-bottom: 8px">
                {{ selectedFactor.name }} 排放限值
              </div>
              <el-table :data="selectedFactor.limits" size="small" style="width: 100%">
                <el-table-column prop="standard_title" label="标准" />
                <el-table-column prop="limit_value" label="限值" width="80">
                  <template #default="{ row }">{{ row.limit_value }} {{ selectedFactor.unit }}</template>
                </el-table-column>
                <el-table-column prop="standard_type" label="类型" width="70">
                  <template #default="{ row }">
                    <el-tag :type="typeMap[row.standard_type]" size="small">{{ typeMap[row.standard_type] }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const router = useRouter()
const devices = ref([])
const standards = ref([])
const news = ref([])
const reports = ref([])
const pollutionFactors = ref([])
const alerts = ref([])
const selectedDevice = ref(null)
const chartData = ref([])
const selectedFactor = ref(null)

const typeMap = {
  national: '',
  industry: 'warning',
  local: 'info',
  international: 'success',
  enterprise: 'danger',
}

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: [selectedFactor.value?.name || '排放值'], bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '15%', top: '10%', containLabel: true },
  xAxis: {
    type: 'category',
    data: chartData.value.map(d => d.time),
    axisLabel: { fontSize: 10, rotate: 30 },
  },
  yAxis: {
    type: 'value',
    name: selectedFactor.value?.unit || '',
    axisLabel: { fontSize: 10 },
  },
  series: [
    {
      name: selectedFactor.value?.name || '排放值',
      type: 'line',
      data: chartData.value.map(d => d.value),
      smooth: true,
      areaStyle: { opacity: 0.1 },
      itemStyle: { color: '#4ade80' },
      markLine: selectedFactor.value?.limits?.length ? {
        data: [{ yAxis: selectedFactor.value.limits[0].limit_value, label: { formatter: '限值' } }],
        lineStyle: { color: '#f56c6c', type: 'dashed' },
      } : undefined,
    },
  ],
}))

const loadDevices = async () => {
  try {
    const res = await api.get('/devices/devices')
    devices.value = res
    if (res.length > 0 && !selectedDevice.value) {
      selectedDevice.value = res[0].id
      loadDeviceData()
    }
  } catch (e) {
    console.error('加载设备失败', e)
  }
}

const loadDeviceData = async () => {
  if (!selectedDevice.value) return
  try {
    const res = await api.get(`/devices/devices/${selectedDevice.value}/readings?hours=24`)
    chartData.value = res.map(r => ({
      time: new Date(r.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      value: r.value,
    }))
  } catch (e) {
    console.error('加载数据失败', e)
  }
}

const loadKnowledge = async () => {
  try {
    const [factors, standardsRes] = await Promise.all([
      api.get('/knowledge/pollution-factors'),
      api.get('/knowledge/standards?limit=50'),
    ])
    pollutionFactors.value = factors
    standards.value = standardsRes
  } catch (e) {
    console.error('加载知识库失败', e)
  }
}

const loadNews = async () => {
  try {
    const res = await api.get('/news/news?limit=5')
    news.value = res
  } catch (e) {
    console.error('加载新闻失败', e)
  }
}

const loadReports = async () => {
  try {
    const res = await api.get('/reports/instances?limit=10')
    reports.value = res
  } catch (e) {
    console.error('加载报告失败', e)
  }
}

const loadAlerts = () => {
  alerts.value = [
    { device: 'DA001 VOCs', message: '排放值达到预警线，建议检查RTO设备', time: '10分钟前' },
    { device: '总排口COD', message: '数值波动较大，建议排查进水浓度', time: '1小时前' },
    { device: 'DA002 SO₂', message: '持续下降趋势，治理效果良好', time: '2小时前' },
  ]
}

const queryFactor = (factor) => {
  selectedFactor.value = factor
}

const removeFactor = (factor) => {
  pollutionFactors.value = pollutionFactors.value.filter(f => f.id !== factor.id)
  if (selectedFactor.value?.id === factor.id) {
    selectedFactor.value = null
  }
}

const openNews = (item) => {
  router.push({ path: '/news', query: { id: item.id } })
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadDevices()
  loadKnowledge()
  loadNews()
  loadReports()
  loadAlerts()
})</script>
