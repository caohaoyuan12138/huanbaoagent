<template>
  <div class="ops-dashboard">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <div class="stat-card stat-online">
          <div class="stat-icon online-icon"><el-icon size="28"><Monitor /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ onlineCount }}</div>
            <div class="stat-label">在线设备</div>
          </div>
          <div class="stat-trend up">{{ allDevices.length }} 台</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-warning">
          <div class="stat-icon warning-icon"><el-icon size="28"><Warning /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ alertStats.unread || 0 }}</div>
            <div class="stat-label">未处理告警</div>
          </div>
          <div class="stat-trend" :class="alertStats.critical ? 'down' : ''">
            {{ alertStats.critical || 0 }} 严重
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-sites">
          <div class="stat-icon site-icon"><el-icon size="28"><OfficeBuilding /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ sites.length }}</div>
            <div class="stat-label">站点/厂区</div>
          </div>
          <div class="stat-trend">个</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-uptime">
          <div class="stat-icon uptime-icon"><el-icon size="28"><Clock /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ avgUptime }}%</div>
            <div class="stat-label">平均可用率</div>
          </div>
          <div class="stat-trend up">稳定</div>
        </div>
      </el-col>
    </el-row>

    <!-- 中间：实时告警 + 设备状态 -->
    <el-row :gutter="16" class="middle-row">
      <!-- 实时告警流 -->
      <el-col :span="8">
        <div class="panel alert-panel">
          <div class="panel-header">
            <span class="panel-title"><el-icon><Bell /></el-icon>实时告警
              <el-badge v-if="alertStats.unread" :value="alertStats.unread" class="alert-badge" />
            </span>
            <el-button size="small" link @click="$router.push('/alerts')">查看全部</el-button>
          </div>
          <div class="alert-list" ref="alertListRef">
            <div v-if="alerts.length === 0" class="empty-alert">
              <el-icon size="32"><CircleCheck /></el-icon><p>暂无告警</p>
            </div>
            <div v-for="alert in alerts.slice(0, 12)" :key="alert.id" class="alert-item" :class="alert.severity">
              <div class="alert-severity">
                <el-tag :type="alert.severity === 'critical' ? 'danger' : 'warning'" size="small">
                  {{ alert.severity === 'critical' ? '严重' : '一般' }}
                </el-tag>
              </div>
              <div class="alert-content">
                <div class="alert-device">{{ deviceName(alert.device_id) }}</div>
                <div class="alert-msg">{{ alert.message }}</div>
              </div>
              <div class="alert-time">{{ formatTime(alert.created_at) }}</div>
            </div>
          </div>
        </div>
      </el-col>

      <!-- 设备实时状态 -->
      <el-col :span="16">
        <div class="panel device-panel">
          <div class="panel-header">
            <span class="panel-title"><el-icon><Monitor /></el-icon>设备实时状态</span>
            <div class="panel-actions">
              <el-select v-model="selectedSite" size="small" placeholder="选择站点" style="width:120px" @change="filterDevices">
                <el-option label="全部站点" :value="null" />
                <el-option v-for="s in sites" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
              <el-button size="small" type="primary" @click="loadAllData">
                <el-icon><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </div>
          <div class="device-grid">
            <div v-for="dev in filteredDevices" :key="dev.id" class="device-card" :class="dev.status"
              @click="$router.push(`/devices?id=${dev.id}`)">
              <div class="device-header">
                <span class="device-name">{{ dev.name }}</span>
                <span class="device-status" :class="dev.status">
                  <span class="status-dot" :class="dev.status" />
                  {{ dev.status === 'online' ? '在线' : dev.status === 'offline' ? '离线' : '告警' }}
                </span>
              </div>
              <div class="device-info">{{ dev.factor }} · {{ dev.unit }}</div>
              <div class="device-value">
                <span class="latest-value">{{ dev.latest_value != null ? dev.latest_value : '--' }}</span>
                <span class="device-location">{{ dev.location || '' }}</span>
              </div>
              <div class="device-health">
                <el-progress :percentage="Math.round(dev.uptime_percent || 0)" :stroke-width="4"
                  :color="getUptimeColor(dev.uptime_percent)" />
                <span class="health-text">{{ dev.latency_ms ? dev.latency_ms.toFixed(0) + 'ms' : '--' }}</span>
              </div>
            </div>
            <div v-if="filteredDevices.length === 0" class="empty-devices">
              <el-icon size="40"><Connection /></el-icon><p>暂无设备</p>
              <el-button type="primary" size="small" @click="$router.push('/devices')">添加设备</el-button>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 底部：站点拓扑 + 趋势 -->
    <el-row :gutter="16" class="bottom-row">
      <el-col :span="12">
        <div class="panel site-panel">
          <div class="panel-header">
            <span class="panel-title"><el-icon><OfficeBuilding /></el-icon>站点分布</span>
          </div>
          <div class="site-tree">
            <div v-if="sites.length === 0" class="empty-sites">
              <el-icon size="32"><Location /></el-icon><p>暂无站点</p>
              <el-button size="small" type="primary" @click="showAddSite = true">创建站点</el-button>
            </div>
            <el-tree v-else :data="siteTreeData" :props="{ label: 'name', children: 'children' }"
              :expand-on-click-node="false" node-key="id" default-expand-all>
              <template #default="{ node, data }">
                <span class="site-tree-node">
                  <el-icon><Location /></el-icon>
                  <span class="site-name">{{ node.label }}</span>
                  <el-tag v-if="data.device_count" size="small" type="info">
                    {{ data.online_count }}/{{ data.device_count }}
                  </el-tag>
                </span>
              </template>
            </el-tree>
          </div>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="panel trend-panel">
          <div class="panel-header">
            <span class="panel-title"><el-icon><TrendCharts /></el-icon>设备读数趋势（最近24小时）</span>
            <el-select v-model="trendDeviceId" size="small" @change="loadTrend" style="width:140px">
              <el-option label="全部设备" :value="null" />
              <el-option v-for="d in allDevices" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
          </div>
          <div ref="trendChartRef" style="height:280px"></div>
        </div>
      </el-col>
    </el-row>

    <!-- 添加站点弹窗 -->
    <el-dialog v-model="showAddSite" title="创建站点" width="400px">
      <el-form :model="newSite" label-width="80px">
        <el-form-item label="站点名称"><el-input v-model="newSite.name" /></el-form-item>
        <el-form-item label="站点编码"><el-input v-model="newSite.code" /></el-form-item>
        <el-form-item label="地址"><el-input v-model="newSite.address" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddSite = false">取消</el-button>
        <el-button type="primary" @click="createSite">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  Monitor, Warning, OfficeBuilding, Clock, Bell, CircleCheck,
  Refresh, Connection, Location, TrendCharts
} from '@element-plus/icons-vue'

const router = useRouter()
const trendChartRef = ref(null)
let ws = null
let trendChart = null
let heartbeatTimer = null

// 数据
const allDevices = ref([])
const alerts = ref([])
const alertStats = ref({ unread: 0, critical: 0, warning: 0 })
const sites = ref([])
const selectedSite = ref(null)
const trendDeviceId = ref(null)
const showAddSite = ref(false)
const newSite = ref({ name: '', code: '', address: '' })

const filteredDevices = computed(() => {
  if (!selectedSite.value) return allDevices.value
  return allDevices.value.filter(d => d.site_id === selectedSite.value)
})

const onlineCount = computed(() => allDevices.value.filter(d => d.status === 'online').length)

const avgUptime = computed(() => {
  if (!allDevices.value.length) return 0
  const sum = allDevices.value.reduce((s, d) => s + (d.uptime_percent || 0), 0)
  return Math.round(sum / allDevices.value.length)
})

const siteTreeData = computed(() => {
  const root = { id: 0, name: '全部站点', device_count: allDevices.value.length, children: [] }
  sites.value.forEach(s => {
    const devCount = allDevices.value.filter(d => d.site_id === s.id).length
    const onlineCount = allDevices.value.filter(d => d.site_id === s.id && d.status === 'online').length
    root.children.push({ ...s, device_count: devCount, online_count: onlineCount, children: [] })
  })
  return [root]
})

function deviceName(deviceId) {
  const d = allDevices.value.find(x => x.id === deviceId)
  return d ? d.name : `设备#${deviceId}`
}

// WebSocket
function connectWebSocket() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const conn = new WebSocket(`${proto}//${location.host}/api/ws/devices`)
  ws = conn

  conn.onopen = () => console.log('WebSocket connected')
  conn.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.type === 'device_data') {
      const dev = allDevices.value.find(d => String(d.id) === data.device_id)
      if (dev) { dev.latest_value = data.value; dev.unit = data.unit; dev.last_seen = data.updated_at }
    } else if (data.type === 'alert') {
      alerts.value.unshift(data)
      if (alerts.value.length > 50) alerts.value.pop()
      loadAlertStats()
    } else if (data.type === 'device_status') {
      const dev = allDevices.value.find(d => String(d.id) === data.device_id)
      if (dev) { dev.status = data.status; dev.last_seen = data.last_seen }
      loadAlertStats()
    } else if (data.type === 'ping') {
      conn.send(JSON.stringify({ type: 'pong' }))
    }
  }
  conn.onclose = () => setTimeout(connectWebSocket, 5000)
  conn.onerror = () => conn.close()
}

// 数据加载
async function loadAllData() {
  try {
    const [devRes, alertRes, siteRes] = await Promise.all([
      fetch('/api/devices/devices'),
      fetch('/api/alerts/stats'),
      fetch('/api/sites'),
    ])
    allDevices.value = (await devRes.json()).value || []
    alertStats.value = await alertRes.json()
    sites.value = (await siteRes.json()).value || []
    loadAlerts()
    loadTrend()
  } catch (e) { console.error('加载数据失败', e) }
}

async function loadAlerts() {
  try {
    const res = await fetch('/api/alerts?status=unread&page_size=20')
    const data = await res.json()
    alerts.value = data.alerts || []
  } catch (e) {}
}

async function loadAlertStats() {
  try {
    const res = await fetch('/api/alerts/stats')
    alertStats.value = await res.json()
  } catch (e) {}
}

async function loadTrend() {
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)

  const charts = []
  const devicesToShow = trendDeviceId.value
    ? allDevices.value.filter(d => d.id === trendDeviceId.value)
    : allDevices.value.filter(d => d.status === 'online').slice(0, 5)

  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
  let series = []
  let allLabels = []

  for (let i = 0; i < devicesToShow.length; i++) {
    const dev = devicesToShow[i]
    try {
      const res = await fetch(`/api/devices/devices/${dev.id}/readings?hours=24&page_size=60`)
      const data = await res.json()
      const readings = (data.value || [])
      const labels = readings.map(r =>
        new Date(r.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      )
      if (readings.length > 0) allLabels = labels
      series.push({
        name: dev.name,
        data: readings.map(r => r.value),
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { color: colors[i % colors.length], width: 2 },
        areaStyle: { opacity: 0.15, color: colors[i % colors.length] },
      })
    } catch (e) {}
  }

  trendChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { data: devicesToShow.map(d => d.name), textStyle: { color: '#888', fontSize: 10 }, top: 0 },
    grid: { top: 35, right: 15, bottom: 30, left: 45 },
    xAxis: { type: 'category', data: allLabels, axisLabel: { color: '#888', fontSize: 9, rotate: 30 } },
    yAxis: { type: 'value', axisLabel: { color: '#888' }, splitLine: { lineStyle: { color: '#f0f0f0' } } },
    series,
  }, true)
}

async function createSite() {
  try {
    const res = await fetch('/api/sites', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newSite.value),
    })
    if (res.ok) {
      ElMessage.success('站点创建成功')
      showAddSite.value = false
      newSite.value = { name: '', code: '', address: '' }
      const siteRes = await fetch('/api/sites')
      sites.value = (await siteRes.json()).value || []
    }
  } catch (e) { ElMessage.error('创建失败') }
}

function getUptimeColor(pct) {
  if (pct >= 95) return '#67c23a'
  if (pct >= 80) return '#e6a23c'
  return '#f56c6c'
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const diff = Math.floor((Date.now() - new Date(timeStr).getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + '分钟前'
  return Math.floor(diff / 3600) + '小时前'
}

function filterDevices() { loadTrend() }

onMounted(() => {
  loadAllData()
  connectWebSocket()
  heartbeatTimer = setInterval(() => { loadAlertStats(); loadAlerts() }, 30000)
})

onUnmounted(() => {
  if (ws) ws.close()
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  if (trendChart) trendChart.dispose()
})
</script>

<style scoped>
.ops-dashboard { padding: 16px; background: #f5f7fa; min-height: 100vh; }
.stat-row { margin-bottom: 16px; }
.stat-card {
  display: flex; align-items: center; padding: 20px; border-radius: 12px;
  background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-icon {
  width: 56px; height: 56px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; margin-right: 16px;
}
.online-icon { background: rgba(103,194,58,0.12); color: #67c23a; }
.warning-icon { background: rgba(230,162,60,0.12); color: #e6a23c; }
.site-icon { background: rgba(64,158,255,0.12); color: #409eff; }
.uptime-icon { background: rgba(124,78,211,0.12); color: #7c4edd; }
.stat-content { flex: 1; }
.stat-value { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.stat-label { font-size: 13px; color: #888; margin-top: 2px; }
.stat-trend { font-size: 12px; color: #888; }
.stat-trend.up { color: #67c23a; }
.stat-trend.down { color: #f56c6c; }
.middle-row, .bottom-row { margin-bottom: 16px; }
.panel {
  background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); overflow: hidden;
}
.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid #f0f0f0;
}
.panel-title { font-size: 15px; font-weight: 600; color: #1a1a2e; display: flex; align-items: center; gap: 6px; }
.panel-actions { display: flex; gap: 8px; align-items: center; }

.alert-list { max-height: 420px; overflow-y: auto; padding: 8px; }
.empty-alert { text-align: center; padding: 40px 0; color: #bbb; }
.empty-alert p { margin-top: 8px; font-size: 14px; }
.alert-item {
  display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px;
  border-radius: 8px; margin-bottom: 4px; transition: background 0.2s; cursor: pointer;
}
.alert-item:hover { background: #f5f7fa; }
.alert-item.critical { background: rgba(245,108,108,0.06); }
.alert-item.warning { background: rgba(230,162,60,0.06); }
.alert-content { flex: 1; min-width: 0; }
.alert-device { font-size: 13px; font-weight: 600; color: #1a1a2e; }
.alert-msg { font-size: 12px; color: #666; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.alert-time { font-size: 11px; color: #aaa; white-space: nowrap; }

.device-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px; padding: 14px; max-height: 480px; overflow-y: auto;
}
.empty-devices { grid-column: 1 / -1; text-align: center; padding: 40px; color: #bbb; }
.empty-devices p { margin: 8px 0 16px; }
.device-card {
  border: 1px solid #e8e8e8; border-radius: 10px; padding: 14px; cursor: pointer;
  transition: all 0.2s; position: relative; overflow: hidden;
}
.device-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.device-card.online::before { background: #67c23a; }
.device-card.offline::before { background: #dcdfe6; }
.device-card:hover { border-color: #409eff; box-shadow: 0 2px 12px rgba(64,158,255,0.12); }
.device-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.device-name { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.device-status { font-size: 12px; display: flex; align-items: center; gap: 4px; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.status-dot.online { background: #67c23a; box-shadow: 0 0 4px #67c23a; }
.status-dot.offline { background: #dcdfe6; }
.device-info { font-size: 12px; color: #888; margin-bottom: 6px; }
.device-value { display: flex; justify-content: space-between; align-items: baseline; }
.latest-value { font-size: 20px; font-weight: 700; color: #1a1a2e; }
.device-location { font-size: 11px; color: #aaa; }
.device-health { margin-top: 8px; display: flex; align-items: center; gap: 6px; }
.health-text { font-size: 11px; color: #aaa; }

.site-tree { padding: 14px; max-height: 300px; overflow-y: auto; }
.empty-sites { text-align: center; padding: 30px; color: #bbb; }
.empty-sites p { margin: 8px 0; }
.site-tree-node { display: flex; align-items: center; gap: 6px; font-size: 13px; }
::v-deep .el-tree-node__content { height: 36px; }
</style>
