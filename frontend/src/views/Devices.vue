<template>
  <div>
    <!-- 设备列表 -->
    <el-row :gutter="16" style="margin-bottom: 16px">
      <el-col :span="18">
        <div class="card">
          <div class="card-header">
            <h3>设备列表</h3>
            <el-button size="small" type="primary" @click="showAddDevice">
              <el-icon><Plus /></el-icon> 添加设备
            </el-button>
          </div>
          <div class="card-body" style="padding: 0">
            <el-table :data="devices" stripe>
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="name" label="设备名称" min-width="200" />
              <el-table-column prop="factor" label="监测因子" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.factor }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="unit" label="单位" width="80" />
              <el-table-column prop="location" label="安装位置" width="160" />
              <el-table-column prop="protocol" label="协议" width="80">
                <template #default="{ row }">
                  <el-tag size="small" type="info">{{ row.protocol }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'online' ? 'success' : 'danger'" size="small">
                    {{ row.status === 'online' ? '在线' : '离线' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="{ row }">
                  <el-button size="small" link @click="analyzeDevice(row)">分析</el-button>
                  <el-button size="small" link type="primary" @click="addReading(row)">录入数据</el-button>
                  <el-button size="small" link type="danger" @click="deleteDevice(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </el-col>

      <!-- 实时数据面板 -->
      <el-col :span="6">
        <div class="card" v-if="selectedDevice">
          <div class="card-header">
            <h3>{{ selectedDevice.name }}</h3>
            <el-tag :type="selectedDevice.status === 'online' ? 'success' : 'danger'" size="small">
              {{ selectedDevice.status === 'online' ? '在线' : '离线' }}
            </el-tag>
          </div>
          <div class="card-body">
            <div style="text-align: center; padding: 16px 0">
              <div style="font-size: 36px; font-weight: 700; color: #4ade80">
                {{ currentAnalysis?.statistics?.recent_avg?.toFixed(2) || '--' }}
              </div>
              <div style="font-size: 14px; color: #666; margin-top: 4px">
                {{ selectedDevice.factor }} / {{ selectedDevice.unit }}
              </div>
              <div style="margin-top: 8px">
                <el-tag :type="trendType(currentAnalysis?.statistics?.trend)" size="small">
                  {{ currentAnalysis?.statistics?.trend || '稳定' }}
                </el-tag>
              </div>
            </div>
            <el-descriptions :column="1" size="small" border>
              <el-descriptions-item label="平均值">{{ currentAnalysis?.statistics?.avg?.toFixed(2) || '--' }} {{ selectedDevice.unit }}</el-descriptions-item>
              <el-descriptions-item label="最大值">{{ currentAnalysis?.statistics?.max?.toFixed(2) || '--' }} {{ selectedDevice.unit }}</el-descriptions-item>
              <el-descriptions-item label="最小值">{{ currentAnalysis?.statistics?.min?.toFixed(2) || '--' }} {{ selectedDevice.unit }}</el-descriptions-item>
              <el-descriptions-item label="排放限值">
                <span style="color: #f56c6c; font-weight: 500">{{ currentAnalysis?.limit || '--' }}</span> {{ selectedDevice.unit }}
              </el-descriptions-item>
              <el-descriptions-item label="数据条数">{{ currentAnalysis?.statistics?.total_readings || 0 }}</el-descriptions-item>
              <el-descriptions-item label="超标次数">
                <span :style="{ color: currentAnalysis?.statistics?.exceed_count > 0 ? '#f56c6c' : '#67c23a', fontWeight: 500 }">
                  {{ currentAnalysis?.statistics?.exceed_count || 0 }}
                </span>
              </el-descriptions-item>
            </el-descriptions>
            <div v-if="currentAnalysis?.suggestions" style="margin-top: 12px">
              <div style="font-size: 12px; font-weight: 500; color: #1a1a1a; margin-bottom: 6px">AI 建议</div>
              <div v-for="(s, i) in currentAnalysis.suggestions" :key="i" style="font-size: 12px; color: #666; padding: 4px 0; border-bottom: 1px solid #f5f5f5">
                {{ s }}
              </div>
            </div>
          </div>
        </div>
        <div class="card" v-else>
          <div class="card-body" style="text-align: center; padding: 40px; color: #999">
            <el-icon :size="32"><Monitor /></el-icon>
            <div style="margin-top: 8px">请选择设备进行分析</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <div class="card" v-if="selectedDevice">
      <div class="card-header">
        <h3>{{ selectedDevice.name }} - 趋势图</h3>
        <el-radio-group v-model="chartHours" size="small" @change="loadChartData">
          <el-radio-button :label="6">6h</el-radio-button>
          <el-radio-button :label="24">24h</el-radio-button>
          <el-radio-button :label="72">72h</el-radio-button>
        </el-radio-group>
      </div>
      <div class="card-body">
        <v-chart :option="chartOption" autoresize style="height: 300px" />
      </div>
    </div>

    <!-- 添加设备弹窗 -->
    <el-dialog v-model="addDeviceVisible" title="添加设备" width="500px">
      <el-form :model="newDevice" label-width="100px">
        <el-form-item label="设备名称">
          <el-input v-model="newDevice.name" placeholder="如：废气排气筒DA001" />
        </el-form-item>
        <el-form-item label="监测因子">
          <el-select v-model="newDevice.factor" style="width: 100%">
            <el-option v-for="f in pollutionFactors" :key="f.symbol" :label="`${f.name}(${f.symbol})`" :value="f.symbol" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="newDevice.unit" placeholder="如：mg/m³" />
        </el-form-item>
        <el-form-item label="安装位置">
          <el-input v-model="newDevice.location" placeholder="如：厂区北侧排气筒" />
        </el-form-item>
        <el-form-item label="通讯协议">
          <el-select v-model="newDevice.protocol" style="width: 100%">
            <el-option label="MQTT" value="mqtt" />
            <el-option label="OPC UA" value="opc_ua" />
            <el-option label="Modbus" value="modbus" />
          </el-select>
        </el-form-item>
        <el-form-item label="Topic">
          <el-input v-model="newDevice.topic" placeholder="如：factory/emission/da001" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDeviceVisible = false">取消</el-button>
        <el-button type="primary" @click="addDevice">确认添加</el-button>
      </template>
    </el-dialog>

    <!-- 录入数据弹窗 -->
    <el-dialog v-model="addReadingVisible" title="录入监测数据" width="400px">
      <el-form :model="newReading" label-width="80px">
        <el-form-item label="监测因子">
          <el-input :value="selectedDevice?.factor" disabled />
        </el-form-item>
        <el-form-item label="监测值">
          <el-input-number v-model="newReading.value" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input :value="selectedDevice?.unit" disabled />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="newReading.status">
            <el-radio label="normal">正常</el-radio>
            <el-radio label="warning">预警</el-radio>
            <el-radio label="exceed">超标</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addReadingVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReading">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TooltipComponent, GridComponent, MarkLineComponent } from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, LineChart, TooltipComponent, GridComponent, MarkLineComponent])

const devices = ref([])
const selectedDevice = ref(null)
const currentAnalysis = ref(null)
const chartHours = ref(24)
const chartData = ref([])
const pollutionFactors = ref([])
const addDeviceVisible = ref(false)
const addReadingVisible = ref(false)

const newDevice = ref({
  name: '',
  factor: 'VOCs',
  unit: 'mg/m³',
  location: '',
  protocol: 'mqtt',
  topic: '',
})

const newReading = ref({
  value: 0,
  status: 'normal',
})

const chartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: [selectedDevice.value?.factor || 'value'], bottom: 0 },
  grid: { left: '3%', right: '4%', bottom: '12%', top: '10%', containLabel: true },
  xAxis: {
    type: 'category',
    data: chartData.value.map(d => d.time),
    axisLabel: { fontSize: 10, rotate: 30 },
  },
  yAxis: {
    type: 'value',
    name: selectedDevice.value?.unit || '',
    axisLabel: { fontSize: 10 },
  },
  series: [
    {
      name: selectedDevice.value?.factor || 'value',
      type: 'line',
      data: chartData.value.map(d => d.value),
      smooth: true,
      areaStyle: { opacity: 0.1 },
      itemStyle: { color: '#4ade80' },
      markLine: currentAnalysis.value?.limit ? {
        data: [{ yAxis: currentAnalysis.value.limit, label: { formatter: '限值' } }],
        lineStyle: { color: '#f56c6c', type: 'dashed' },
      } : undefined,
    },
  ],
}))

const loadDevices = async () => {
  try {
    devices.value = await api.get('/devices/devices')
  } catch (e) {
    ElMessage.error('加载设备失败')
  }
}

const loadFactors = async () => {
  try {
    pollutionFactors.value = await api.get('/knowledge/pollution-factors')
  } catch (e) {
    console.error('加载因子失败', e)
  }
}

const analyzeDevice = async (device) => {
  selectedDevice.value = device
  try {
    const res = await api.get(`/devices/devices/${device.id}/analysis`)
    currentAnalysis.value = res
    loadChartData()
  } catch (e) {
    ElMessage.error('分析失败')
  }
}

const loadChartData = async () => {
  if (!selectedDevice.value) return
  try {
    const res = await api.get(`/devices/devices/${selectedDevice.value.id}/readings?hours=${chartHours.value}`)
    chartData.value = res.map(r => ({
      time: new Date(r.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      value: r.value,
    }))
  } catch (e) {
    console.error('加载图表数据失败', e)
  }
}

const showAddDevice = () => {
  addDeviceVisible.value = true
}

const addDevice = async () => {
  try {
    await api.post('/devices/devices', newDevice.value)
    ElMessage.success('设备添加成功')
    addDeviceVisible.value = false
    newDevice.value = { name: '', factor: 'VOCs', unit: 'mg/m³', location: '', protocol: 'mqtt', topic: '' }
    loadDevices()
  } catch (e) {
    ElMessage.error('添加失败: ' + (e.response?.data?.detail || e.message))
  }
}

const addReading = (device) => {
  selectedDevice.value = device
  addReadingVisible.value = true
}

const submitReading = async () => {
  if (!selectedDevice.value) return
  try {
    await api.post(`/devices/devices/${selectedDevice.value.id}/readings`, {
      device_id: selectedDevice.value.id,
      factor: selectedDevice.value.factor,
      value: newReading.value,
      unit: selectedDevice.value.unit,
      timestamp: new Date().toISOString(),
      status: newReading.status,
    })
    ElMessage.success('数据录入成功')
    addReadingVisible.value = false
    newReading.value = { value: 0, status: 'normal' }
    analyzeDevice(selectedDevice.value)
  } catch (e) {
    ElMessage.error('录入失败')
  }
}

const deleteDevice = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该设备？', '提示', { type: 'warning' })
    await api.delete(`/devices/devices/${id}`)
    ElMessage.success('删除成功')
    loadDevices()
    if (selectedDevice.value?.id === id) {
      selectedDevice.value = null
      currentAnalysis.value = null
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const trendType = (trend) => {
  if (trend === '上升') return 'danger'
  if (trend === '下降') return 'success'
  return 'info'
}

watch(chartHours, () => {
  loadChartData()
})

onMounted(() => {
  loadDevices()
  loadFactors()
})
</script>
