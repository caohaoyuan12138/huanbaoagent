<template>
  <div>
    <!-- 创建合规检查 -->
    <div class="card" style="margin-bottom: 16px">
      <div class="card-header">
        <h3><el-icon><Check /></el-icon> 新建合规检查</h3>
      </div>
      <div class="card-body">
        <el-form :model="form" label-width="100px" inline>
          <el-form-item label="检查名称">
            <el-input v-model="form.name" placeholder="如：2026年Q2季度合规检查" style="width: 260px" />
          </el-form-item>
          <el-form-item label="选择设备">
            <el-select v-model="form.device_ids" multiple placeholder="选择设备" style="width: 300px">
              <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="checking" @click="startCheck">
              <el-icon><CaretRight /></el-icon> 开始检查
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 检查结果统计 -->
    <el-row :gutter="16" style="margin-bottom: 16px" v-if="lastResult">
      <el-col :span="6">
        <div class="stat-card" style="border-left: 4px solid #67c23a">
          <div class="stat-label">通过</div>
          <div class="stat-value" style="color: #67c23a">{{ lastResult.passed_count }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="border-left: 4px solid #f59e0b">
          <div class="stat-label">警告</div>
          <div class="stat-value" style="color: #f59e0b">{{ lastResult.warning_count }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="border-left: 4px solid #f56c6c">
          <div class="stat-label">不合格</div>
          <div class="stat-value" style="color: #f56c6c">{{ lastResult.failed_count }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" style="border-left: 4px solid #4ade80">
          <div class="stat-label">检查设备</div>
          <div class="stat-value">{{ lastResult.passed_count + lastResult.warning_count + lastResult.failed_count }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 检查结果详情 -->
    <div class="card" v-if="lastResult?.details?.length">
      <div class="card-header">
        <h3>检查结果详情</h3>
      </div>
      <div class="card-body" style="padding: 0">
        <el-table :data="lastResult.details" stripe>
          <el-table-column prop="device_name" label="设备名称" min-width="180" />
          <el-table-column prop="factor" label="因子" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.factor }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="实测值" width="100">
            <template #default="{ row }">
              <span :style="{ color: row.status === 'failed' ? '#f56c6c' : row.status === 'warning' ? '#f59e0b' : '#67c23a', fontWeight: 600 }">
                {{ row.value }}
              </span>
              <span style="color: #999; font-size: 12px">{{ row.unit }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="limit_value" label="限值" width="100">
            <template #default="{ row }">
              {{ row.limit_value }} {{ row.unit }}
            </template>
          </el-table-column>
          <el-table-column prop="limit_source" label="限值来源" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" label="结果" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'passed' ? 'success' : row.status === 'warning' ? 'warning' : 'danger'" size="small">
                {{ row.status === 'passed' ? '通过' : row.status === 'warning' ? '警告' : '不合格' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="说明" min-width="200" show-overflow-tooltip />
        </el-table>
      </div>
    </div>

    <!-- 历史检查记录 -->
    <div class="card">
      <div class="card-header">
        <h3>历史检查记录</h3>
        <el-button size="small" type="success" @click="seedCheck">
          <el-icon><Download /></el-icon> 生成示例
        </el-button>
      </div>
      <div class="card-body" style="padding: 0">
        <el-table :data="checks" stripe v-loading="loading">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column prop="name" label="检查名称" min-width="180" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'running' ? 'warning' : 'info'" size="small">
                {{ row.status === 'completed' ? '已完成' : row.status === 'running' ? '检查中' : '待执行' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="结果" width="200">
            <template #default="{ row }">
              <span style="color: #67c23a">通过 {{ row.passed_count }}</span>
              <span style="color: #f59e0b; margin: 0 8px">警告 {{ row.warning_count }}</span>
              <span style="color: #f56c6c">不合格 {{ row.failed_count }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="result_summary" label="摘要" min-width="200" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="runCheck(row)">重新检查</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="padding: 12px; display: flex; justify-content: flex-end">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="loadChecks"
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

const devices = ref([])
const checks = ref([])
const lastResult = ref(null)
const loading = ref(false)
const checking = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const form = ref({ name: '', device_ids: [] })

const loadDevices = async () => {
  try {
    devices.value = await api.get('/devices/devices')
  } catch (e) {
    console.error('加载设备失败', e)
  }
}

const loadChecks = async () => {
  loading.value = true
  try {
    const res = await api.get('/compliance/checks', { params: { page: page.value, page_size: pageSize.value } })
    checks.value = res.checks
    total.value = res.total
  } catch (e) {
    console.error('加载检查记录失败', e)
  } finally {
    loading.value = false
  }
}

const startCheck = async () => {
  if (!form.value.device_ids?.length) {
    ElMessage.warning('请先选择设备')
    return
  }
  checking.value = true
  try {
    const res = await api.post('/compliance/check', {
      name: form.value.name || '手动合规检查',
      device_ids: form.value.device_ids,
      standard_ids: [],
    })
    await runCheck({ id: res.id, device_ids: form.value.device_ids })
  } catch (e) {
    ElMessage.error('创建检查失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    checking.value = false
  }
}

const runCheck = async (check) => {
  try {
    const res = await api.post(`/compliance/checks/${check.id}/results`)
    lastResult.value = res
    ElMessage.success('合规检查完成')
  } catch (e) {
    ElMessage.error('检查失败: ' + (e.response?.data?.detail || e.message))
  }
}

const seedCheck = async () => {
  try {
    await api.post('/compliance/seed')
    ElMessage.success('示例检查已生成')
    loadChecks()
  } catch (e) {
    ElMessage.error('生成失败')
  }
}

const formatTime = (t) => {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN')
}

onMounted(() => {
  loadDevices()
  loadChecks()
})
</script>
