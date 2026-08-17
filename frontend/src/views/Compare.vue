<template>
  <div>
    <!-- 因子选择 -->
    <div class="card" style="margin-bottom: 16px">
      <div class="card-header">
        <h3><el-icon><Ratio /></el-icon> 标准限值对比分析</h3>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-input v-model="searchKeyword" placeholder="搜索因子..." clearable style="width: 200px" @input="handleSearch" />
          <el-select v-model="selectedFactors" multiple placeholder="选择对比因子" collapse-tags style="width: 300px">
            <el-option v-for="f in filteredFactors" :key="f.id" :label="`${f.name} (${f.symbol})`" :value="f.id" />
          </el-select>
          <el-button type="primary" :loading="comparing" @click="compareLimits">
            <el-icon><Search /></el-icon> 对比分析
          </el-button>
        </div>
      </div>
    </div>

    <!-- 对比结果 -->
    <div v-if="compareResult?.results?.length" class="card" style="margin-bottom: 16px">
      <div class="card-header">
        <h3>限值差异分析</h3>
      </div>
      <div class="card-body" style="padding: 0">
        <el-table :data="compareResult.results" stripe>
          <el-table-column prop="symbol" label="因子" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ row.symbol }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="中文名称" width="120" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column label="最严限值" width="120">
            <template #default="{ row }">
              <span style="color: #67c23a; font-weight: 600">{{ row.diff?.strictest?.limit_value ?? '-' }} {{ row.unit }}</span>
              <div style="font-size: 11px; color: #999">{{ row.diff?.strictest?.standard_type ?? '' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="最松限值" width="120">
            <template #default="{ row }">
              <span style="color: #f56c6c; font-weight: 600">{{ row.diff?.loosest?.limit_value ?? '-' }} {{ row.unit }}</span>
              <div style="font-size: 11px; color: #999">{{ row.diff?.loosest?.standard_type ?? '' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="差异" width="120">
            <template #default="{ row }">
              <span :style="{ color: row.diff?.has_variation ? '#f56c6c' : '#67c23a' }">
                {{ row.diff?.difference?.value ?? '-' }} {{ row.unit }}
              </span>
              <div style="font-size: 11px; color: #999">倍率 {{ row.diff?.difference?.max_ratio ?? '-' }}</div>
            </template>
          </el-table-column>
          <el-table-column label="涉及标准数" width="100">
            <template #default="{ row }">
              {{ Object.keys(row.standards).length }}
            </template>
          </el-table-column>
          <el-table-column label="限值明细" min-width="300">
            <template #default="{ row }">
              <div v-for="(entries, st) in row.standards" :key="st" style="margin-bottom: 6px">
                <el-tag size="small" type="info" style="margin-right: 8px">{{ st }}</el-tag>
                <span style="font-size: 12px; color: #666">
                  {{ entries[0]?.limit_value ?? '-' }} {{ entries[0]?.unit ?? row.unit }}
                  <span style="color: #999; font-size: 11px">— {{ entries[0]?.standard_title }}</span>
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 全部因子限值表 -->
    <div class="card">
      <div class="card-header">
        <h3>所有因子限值汇总</h3>
        <span style="font-size: 12px; color: #999">共 {{ factors.length }} 个因子</span>
      </div>
      <div class="card-body" style="padding: 0; max-height: 500px; overflow-y: auto">
        <el-table :data="factors" stripe size="small" style="width: 100%">
          <el-table-column prop="symbol" label="符号" width="80" />
          <el-table-column prop="name" label="名称" width="120" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="limit_count" label="限值条数" width="90" />
          <el-table-column label="各标准限值" min-width="400">
            <template #default="{ row }">
              <div v-for="(entries, st) in row.limits_by_standard" :key="st" style="margin-bottom: 4px">
                <el-tag size="small" type="info" style="margin-right: 6px">{{ st }}</el-tag>
                <span style="font-size: 11px; color: #666">
                  {{ entries[0]?.limit_value ?? '-' }} {{ entries[0]?.unit ?? row.unit }}
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Ratio } from '@element-plus/icons-vue'
import api from '@/api'

const factors = ref([])
const selectedFactors = ref([])
const searchKeyword = ref('')
const compareResult = ref(null)
const comparing = ref(false)

const filteredFactors = computed(() => {
  if (!searchKeyword.value) return factors.value
  const kw = searchKeyword.value.toLowerCase()
  return factors.value.filter(f =>
    f.symbol.toLowerCase().includes(kw) ||
    f.name.toLowerCase().includes(kw)
  )
})

const loadFactors = async () => {
  try {
    factors.value = await api.get('/compare/factors')
  } catch (e) {
    console.error('加载因子失败', e)
  }
}

const compareLimits = async () => {
  if (!selectedFactors.value.length) {
    ElMessage.warning('请先选择要对比的因子')
    return
  }
  comparing.value = true
  try {
    compareResult.value = await api.post('/compare/limits', {
      factor_ids: selectedFactors.value,
    })
  } catch (e) {
    ElMessage.error('对比失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    comparing.value = false
  }
}

const handleSearch = () => {
  // computed handles filtering
}

onMounted(() => {
  loadFactors()
})
</script>
