<template>
  <div>
    <!-- 统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">未读告警</div>
          <div class="stat-value" style="color: #f59e0b">{{ stats.unread || 0 }}</div>
          <div class="stat-change">待处理</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">严重告警</div>
          <div class="stat-value" style="color: #f56c6c">{{ stats.by_severity?.critical || 0 }}</div>
          <div class="stat-change">需要立即处理</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">一般告警</div>
          <div class="stat-value" style="color: #4ade80">{{ stats.by_severity?.warning || 0 }}</div>
          <div class="stat-change">注意观察</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-label">未解决</div>
          <div class="stat-value" style="color: #a78bfa">{{ stats.unresolved || 0 }}</div>
          <div class="stat-change">待跟进</div>
        </div>
      </el-col>
    </el-row>

    <!-- 告警列表 -->
    <div class="card">
      <div class="card-header">
        <h3>告警列表</h3>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-select v-model="filterSeverity" size="small" placeholder="级别" clearable style="width: 100px">
            <el-option label="全部" value="" />
            <el-option label="严重" value="critical" />
            <el-option label="一般" value="warning" />
          </el-select>
          <el-select v-model="filterStatus" size="small" placeholder="状态" clearable style="width: 100px">
            <el-option label="全部" value="" />
            <el-option label="未读" value="unread" />
            <el-option label="已读" value="read" />
            <el-option label="已解决" value="resolved" />
          </el-select>
          <el-button size="small" type="success" @click="seedAlerts">
            <el-icon><Download /></el-icon> 生成示例
          </el-button>
          <el-button size="small" @click="loadAlerts">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>
      <div class="card-body" style="padding: 0">
        <el-table :data="alerts" stripe v-loading="loading">
          <el-table-column prop="severity" label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'critical' ? 'danger' : 'warning'" size="small">
                {{ row.severity === 'critical' ? '严重' : '一般' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="factor" label="因子" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.factor }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="当前值" width="100">
            <template #default="{ row }">
              <span :style="{ color: row.severity === 'critical' ? '#f56c6c' : '#f59e0b', fontWeight: 600 }">
                {{ row.value }}
              </span>
              <span style="color: #999; font-size: 12px">{{ row.unit }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="limit_value" label="限值" width="90">
            <template #default="{ row }">
              {{ row.limit_value }} {{ row.unit }}
            </template>
          </el-table-column>
          <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="160">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'unread'" size="small" link @click="markRead(row.id)">已读</el-button>
              <el-button v-if="row.status !== 'resolved'" size="small" link type="success" @click="resolveAlert(row.id)">解决</el-button>
              <el-button size="small" link type="danger" @click="deleteAlert(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="padding: 12px; display: flex; justify-content: flex-end">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="loadAlerts"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const alerts = ref([])
const stats = ref({ unread: 0, unresolved: 0, by_severity: {} })
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterSeverity = ref('')
const filterStatus = ref('')

const loadAlerts = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filterSeverity.value) params.severity = filterSeverity.value
    if (filterStatus.value) params.status = filterStatus.value
    const res = await api.get('/alerts', { params })
    alerts.value = res.alerts
    total.value = res.total
  } catch (e) {
    console.error('加载告警失败', e)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    stats.value = await api.get('/alerts/stats')
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

const markRead = async (id) => {
  try {
    await api.put(`/alerts/${id}/read`)
    ElMessage.success('已标记为已读')
    loadAlerts()
    loadStats()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const resolveAlert = async (id) => {
  try {
    await api.put(`/alerts/${id}/resolve`)
    ElMessage.success('已标记为已解决')
    loadAlerts()
    loadStats()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const deleteAlert = async (id) => {
  try {
    await api.delete(`/alerts/${id}`)
    ElMessage.success('已删除')
    loadAlerts()
    loadStats()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const seedAlerts = async () => {
  try {
    await api.post('/alerts/seed')
    ElMessage.success('示例告警已生成')
    loadAlerts()
    loadStats()
  } catch (e) {
    ElMessage.error('生成失败: ' + (e.response?.data?.detail || e.message))
  }
}

const statusType = (s) => {
  const map = { unread: 'danger', read: 'info', resolved: 'success' }
  return map[s] || ''
}

const statusLabel = (s) => {
  const map = { unread: '未读', read: '已读', resolved: '已解决' }
  return map[s] || s
}

const formatTime = (t) => {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN')
}

onMounted(() => {
  loadAlerts()
  loadStats()
})
</script>
