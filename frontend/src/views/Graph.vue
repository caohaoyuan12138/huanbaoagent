<template>
  <div class="graph-page">
    <div class="page-header">
      <h3>环保知识图谱</h3>
      <div class="header-actions">
        <el-input
          v-model="keyword"
          placeholder="搜索因子/标准..."
          clearable
          style="width: 220px"
          @change="handleSearch"
          @clear="handleSearch"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select
          v-model="selectedIndustry"
          placeholder="行业筛选"
          clearable
          style="width: 160px"
          @change="handleIndustryChange"
        >
          <el-option label="全部" value="" />
          <el-option label="化工" value="化工" />
          <el-option label="电力" value="电力" />
          <el-option label="钢铁" value="钢铁" />
          <el-option label="建材" value="建材" />
          <el-option label="冶金" value="冶金" />
          <el-option label="造纸" value="造纸" />
          <el-option label="印染" value="印染" />
        </el-select>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="因子关系图" name="factors">
        <div class="graph-container">
          <div class="legend">
            <div class="legend-item"><span class="dot" style="background:#4ade80"></span>污染因子</div>
            <div class="legend-item"><span class="dot" style="background:#fb923c"></span>排放限值</div>
          </div>
          <div v-if="loadingFactors" class="loading">加载中...</div>
          <v-chart
            v-else
            ref="factorChartRef"
            :option="factorChartOption"
            autoresize
            style="height: calc(100vh - 200px)"
            @click="onNodeClick"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane label="标准覆盖图" name="standards">
        <div class="graph-container">
          <div class="legend">
            <div class="legend-item"><span class="dot" style="background:#60a5fa"></span>环保标准</div>
            <div class="legend-item"><span class="dot" style="background:#4ade80"></span>污染因子</div>
          </div>
          <div v-if="loadingStandards" class="loading">加载中...</div>
          <v-chart
            v-else
            ref="stdChartRef"
            :option="stdChartOption"
            autoresize
            style="height: calc(100vh - 200px)"
            @click="onNodeClick"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="detailVisible"
      :title="selectedNode?.name || selectedNode?.label || '节点详情'"
      width="480px"
      destroy-on-close
    >
      <div v-if="selectedNode" class="node-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="节点类型">
            <el-tag :type="nodeTypeTag(selectedNode.type)" size="small">
              {{ nodeTypeLabel(selectedNode.type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.symbol" label="因子代号">
            {{ selectedNode.symbol }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.unit" label="单位">
            {{ selectedNode.unit }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.standard_type" label="标准类型">
            {{ selectedNode.standard_type }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.limit_value !== undefined" label="排放限值">
            ≤{{ selectedNode.limit_value }} {{ selectedNode.unit || '' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.standard" label="适用标准">
            {{ selectedNode.standard }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.industry" label="适用行业">
            {{ selectedNode.industry }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.category" label="污染类别">
            {{ selectedNode.category }}
          </el-descriptions-item>
          <el-descriptions-item v-if="selectedNode.description" label="描述">
            {{ selectedNode.description }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="connectedEdges.length > 0" class="connections">
          <div class="connections-title">关联关系</div>
          <el-tag
            v-for="edge in connectedEdges"
            :key="edge.source + edge.target"
            size="small"
            class="edge-tag"
          >
            {{ edge.relation }} → {{ getNodeLabel(edge.target) }}
          </el-tag>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { GraphChart } from 'echarts/charts'
import {
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import api from '@/api'

use([CanvasRenderer, GraphChart, TooltipComponent, LegendComponent, TitleComponent])

const activeTab = ref('factors')
const keyword = ref('')
const selectedIndustry = ref('')
const loadingFactors = ref(false)
const loadingStandards = ref(false)
const factorChartRef = ref(null)
const stdChartRef = ref(null)
const detailVisible = ref(false)
const selectedNode = ref(null)

const factorData = ref({ nodes: [], edges: [] })
const stdData = ref({ nodes: [], edges: [] })

const COLORS = {
  standard: '#60a5fa',
  factor: '#4ade80',
  limit: '#fb923c',
}

const factorChartOption = computed(() => buildGraphOption(factorData.value.nodes, factorData.value.edges))
const stdChartOption = computed(() => buildGraphOption(stdData.value.nodes, stdData.value.edges))

function nodeTypeTag(type) {
  const map = { standard: 'primary', factor: 'success', limit: 'warning' }
  return map[type] || 'info'
}

function nodeTypeLabel(type) {
  const map = { standard: '环保标准', factor: '污染因子', limit: '排放限值' }
  return map[type] || type
}

function getNodeLabel(nodeId) {
  const node = [...factorData.value.nodes, ...stdData.value.nodes].find(n => n.id === nodeId)
  return node?.label || nodeId
}

function buildGraphOption(nodes, edges) {
  const categoryCounts = { standard: 0, factor: 0, limit: 0 }
  nodes.forEach(n => { categoryCounts[n.type] = (categoryCounts[n.type] || 0) + 1 })

  return {
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'node') {
          const d = params.data
          let html = `<strong>${d.name || d.label}</strong><br/>`
          html += `<span style="color:#999">类型：</span>${nodeTypeLabel(d.type)}<br/>`
          if (d.unit) html += `<span style="color:#999">单位：</span>${d.unit}<br/>`
          if (d.standard) html += `<span style="color:#999">标准：</span>${d.standard}<br/>`
          if (d.limit_value !== undefined) html += `<span style="color:#999">限值：</span>≤${d.limit_value} ${d.unit || ''}<br/>`
          if (d.industry) html += `<span style="color:#999">行业：</span>${d.industry}<br/>`
          if (d.category) html += `<span style="color:#999">类别：</span>${d.category}<br/>`
          return html
        }
        return `${params.data.source} → ${params.data.target}`
      },
    },
    legend: {
      bottom: 10,
      data: Object.entries(categoryCounts)
        .filter(([_, c]) => c > 0)
        .map(([type, _]) => nodeTypeLabel(type)),
      textStyle: { fontSize: 12 },
      icon: 'circle',
      itemWidth: 10,
      itemHeight: 10,
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: {
          repulsion: 300,
          gravity: 0.08,
          edgeLength: [80, 200],
          layoutAnimation: true,
        },
        data: nodes.map(n => ({
          ...n,
          name: n.label,  // ECharts uses 'name' for node identity
          symbolSize: n.type === 'standard' ? 50 : n.type === 'limit' ? 30 : 36,
          itemStyle: { color: COLORS[n.type] || '#999' },
          label: {
            show: true,
            fontSize: 11,
            position: 'right',
            formatter: (params) => {
              const maxLen = params.data.type === 'standard' ? 18 : 12
              const text = params.data.name || ''
              return text.length > maxLen ? text.slice(0, maxLen) + '…' : text
            },
          },
        })),
        edges: edges.map(e => ({
          source: e.source,
          target: e.target,
          lineStyle: {
            color: '#bbb',
            width: 1.5,
            curveness: 0.2,
          },
          label: {
            show: true,
            fontSize: 10,
            formatter: e.relation === 'limit_of' ? '≤' : '',
            position: 'middle',
          },
        })),
        roam: true,
        draggable: true,
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3 },
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
        },
        categories: [
          { name: 'standard', itemStyle: { color: COLORS.standard } },
          { name: 'factor', itemStyle: { color: COLORS.factor } },
          { name: 'limit', itemStyle: { color: COLORS.limit } },
        ].filter((_, i) => categoryCounts[[,'standard','factor','limit'][i+1]] > 0),
      },
    ],
  }
}

async function loadFactorGraph() {
  loadingFactors.value = true
  try {
    const params = new URLSearchParams()
    if (keyword.value) params.set('keyword', keyword.value)
    if (selectedIndustry.value) params.set('standard_type', selectedIndustry.value)
    const res = await api.get(`/graph/factors?${params}`)
    factorData.value = res
  } catch (e) {
    ElMessage.error('加载因子图谱失败')
  } finally {
    loadingFactors.value = false
  }
}

async function loadStandardGraph() {
  loadingStandards.value = true
  try {
    const params = new URLSearchParams()
    if (keyword.value) params.set('keyword', keyword.value)
    if (selectedIndustry.value) params.set('industry', selectedIndustry.value)
    const res = await api.get(`/graph/standards?${params}`)
    stdData.value = res
  } catch (e) {
    ElMessage.error('加载标准图谱失败')
  } finally {
    loadingStandards.value = false
  }
}

function onTabChange(tab) {
  if (tab === 'factors' && factorData.value.nodes.length === 0) {
    loadFactorGraph()
  } else if (tab === 'standards' && stdData.value.nodes.length === 0) {
    loadStandardGraph()
  }
}

function handleSearch() {
  if (activeTab.value === 'factors') {
    loadFactorGraph()
  } else {
    loadStandardGraph()
  }
}

function handleIndustryChange() {
  if (activeTab.value === 'factors') {
    loadFactorGraph()
  } else {
    loadStandardGraph()
  }
}

const connectedEdges = computed(() => {
  if (!selectedNode.value) return []
  const id = selectedNode.value.id
  const data = activeTab.value === 'factors' ? factorData.value : stdData.value
  return data.edges.filter(e => e.source === id || e.target === id)
})

function onNodeClick(params) {
  if (params.dataType === 'node') {
    selectedNode.value = params.data
    detailVisible.value = true
  }
}

onMounted(() => {
  loadFactorGraph()
})

onBeforeUnmount(() => {
  factorData.value = { nodes: [], edges: [] }
  stdData.value = { nodes: [], edges: [] }
})
</script>

<style scoped>
.graph-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.page-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.legend {
  position: absolute;
  top: 12px;
  right: 12px;
  background: rgba(255, 255, 255, 0.92);
  border-radius: 8px;
  padding: 10px 14px;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #555;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 14px;
}

.node-detail .connections {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.connections-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.edge-tag {
  margin: 2px 4px 2px 0;
  cursor: pointer;
}
</style>
