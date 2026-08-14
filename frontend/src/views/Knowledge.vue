<template>
  <div class="knowledge-page">
    <div class="card" style="height: 100%; display: flex; flex-direction: column;">
      <div class="card-header">
        <h3>环保法律法规标准库</h3>
        <div style="display: flex; gap: 8px">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索标准名称或编号..."
            clearable
            style="width: 250px"
            @input="handleSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button type="primary" @click="showAddDialog"><el-icon><Plus /></el-icon> 添加标准</el-button>
        </div>
      </div>
      <div style="flex: 1; overflow: hidden;">
        <el-table
          :data="pagedStandards"
          stripe
          style="width: 100%"
          v-loading="loading"
          @row-click="selectStandard"
          height="100%"
        >
          <el-table-column label="标准编号" min-width="140">
            <template #default="{ row }">
              <span style="font-weight: 600; color: #22c55e">{{ row.standard_number || parseStandardNumber(row.title) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="标准名称" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.title }}
            </template>
          </el-table-column>
          <el-table-column label="类别" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="getCategoryTag(row.category)" effect="plain">{{ row.category || '其他' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="适用行业" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.industry || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="发布日期" width="120" align="center">
            <template #default="{ row }">
              {{ formatDate(row.publish_date) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" align="center" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click.stop="selectStandard(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div style="padding: 12px; display: flex; justify-content: flex-end; border-top: 1px solid #f0f0f0;">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalCount"
          layout="total, prev, pager, next, jumper"
          small
          @current-change="loadStandards"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="selectedStandard?.title || '标准详情'" width="900px" destroy-on-close>
      <template v-if="selectedStandard">
        <div class="detail-meta">
          <el-tag size="small" :type="getCategoryTag(selectedStandard.category)">{{ selectedStandard.category || '其他' }}</el-tag>
          <el-tag size="small" type="info" effect="plain">{{ getTypeInfo(selectedStandard.standard_type).label }}</el-tag>
          <span v-if="selectedStandard.industry" class="meta-text">适用行业：{{ selectedStandard.industry }}</span>
          <span class="meta-text">发布：{{ formatDate(selectedStandard.publish_date) }}</span>
          <span class="meta-text">实施：{{ formatDate(selectedStandard.implement_date) }}</span>
        </div>

        <!-- 标准基本信息 -->
        <div class="detail-info" v-if="selectedStandard.content">
          <div class="info-label">标准摘要</div>
          <div class="info-content">{{ selectedStandard.content }}</div>
        </div>

        <!-- 污染因子限值表 -->
        <div class="limits-section">
          <div class="section-title">
            <span>污染因子排放限值</span>
            <el-tag size="small" type="warning">{{ detailLimits.length }} 项</el-tag>
          </div>
          <el-table :data="detailLimits" stripe style="width: 100%" v-loading="detailLoading" empty-text="该标准暂无限值数据">
            <el-table-column label="污染因子" min-width="160">
              <template #default="{ row }">
                <div style="font-weight: 500">{{ row.factor_name }}</div>
                <div style="font-size: 12px; color: #999">符号：{{ row.factor_symbol }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="limit_value" label="排放限值" width="120" align="center">
              <template #default="{ row }">
                <span style="font-size: 15px; font-weight: 600; color: #e6a23c">{{ row.limit_value }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="100" align="center" />
            <el-table-column prop="standard_type" label="标准类型" width="120" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="getTypeInfo(row.standard_type).type">{{ getTypeInfo(row.standard_type).label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
          </el-table>
        </div>

        <!-- 来源链接 -->
        <div class="source-section" v-if="selectedStandard.pdf_url">
          <el-link :href="selectedStandard.pdf_url.startsWith('http') ? selectedStandard.pdf_url : 'https://www.mee.gov.cn' + selectedStandard.pdf_url" target="_blank" type="primary">
            <el-icon><Download /></el-icon> 下载标准PDF原文
          </el-link>
          <span v-if="selectedStandard.source_url && selectedStandard.source_url !== selectedStandard.pdf_url" class="meta-text" style="margin-left:12px">
            <el-icon><Link /></el-icon> 网页版: {{ selectedStandard.source_url }}
          </span>
        </div>
      </template>
    </el-dialog>

    <!-- 添加标准弹窗 -->
    <el-dialog v-model="addVisible" title="添加标准" width="600px">
      <el-form :model="newStandard" label-width="100px">
        <el-form-item label="标准名称">
          <el-input v-model="newStandard.title" placeholder="如：GB 16297-1996 大气污染物综合排放标准" />
        </el-form-item>
        <el-form-item label="标准类型">
          <el-select v-model="newStandard.standard_type" style="width: 100%">
            <el-option label="国家标准(GB)" value="national" />
            <el-option label="行业标准(HJ/SY)" value="industry" />
            <el-option label="地方标准(DB)" value="local" />
            <el-option label="国际标准" value="international" />
            <el-option label="企业标准" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="污染类别">
          <el-select v-model="newStandard.category" style="width: 100%" placeholder="选择类别">
            <el-option label="废气" value="废气" />
            <el-option label="废水" value="废水" />
            <el-option label="固废" value="固废" />
            <el-option label="噪声" value="噪声" />
            <el-option label="土壤" value="土壤" />
            <el-option label="地下水" value="地下水" />
            <el-option label="环境空气" value="环境空气" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用行业">
          <el-input v-model="newStandard.industry" placeholder="如：石油化工,制药" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-date-picker v-model="newStandard.publish_date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="标准内容">
          <el-input v-model="newStandard.content" type="textarea" :rows="3" placeholder="标准内容摘要" />
        </el-form-item>
        <el-form-item label="来源链接">
          <el-input v-model="newStandard.source_url" placeholder="https://" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" @click="addStandard">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const loading = ref(false)
const detailLoading = ref(false)
const standards = ref([])
const selectedStandard = ref(null)
const detailLimits = ref([])
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = 50
const totalCount = ref(0)
const addVisible = ref(false)
const detailVisible = ref(false)

const newStandard = ref({
  title: '',
  standard_type: 'national',
  category: '',
  industry: '',
  publish_date: null,
  content: '',
  source_url: '',
})

const typeMap = {
  national: { type: '', label: '国家标准' },
  industry: { type: 'warning', label: '行业标准' },
  local: { type: 'info', label: '地方标准' },
  international: { type: 'success', label: '国际标准' },
  enterprise: { type: 'danger', label: '企业标准' },
}

const getTypeInfo = (standardType) => {
  return typeMap[standardType] || { type: 'info', label: standardType || '其他' }
}

const categoryTagMap = {
  '废气': 'warning',
  '废水': '',
  '固废': 'info',
  '噪声': 'danger',
  '土壤': 'success',
  '地下水': 'success',
  '环境空气': '',
}

const getCategoryTag = (category) => {
  return categoryTagMap[category] || 'info'
}

// 从标题中解析标准编号，如 "GB 16297-1996 大气污染物综合排放标准" → "GB 16297-1996"
const parseStandardNumber = (title) => {
  if (!title) return ''
  const match = title.match(/^([A-Z]{1,6}[\s/]*\d+(?:\.\d+)?-\d+)/)
  return match ? match[1].trim() : title.substring(0, 20)
}

// 从标题中解析标准名称
const parseStandardName = (title) => {
  if (!title) return ''
  const match = title.match(/^[A-Z]{1,6}[\s/]*\d+(?:\.\d+)?-\d+\s*(.+)/)
  return match ? match[1].trim() : title
}

const pagedStandards = computed(() => standards.value)

let searchTimer = null
const handleSearch = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    loadStandards()
  }, 400)
}

const loadStandards = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      page: String(currentPage.value),
      page_size: String(pageSize),
    })
    if (searchKeyword.value) {
      params.set('keyword', searchKeyword.value)
    }
    const res = await api.get(`/knowledge/standards?${params.toString()}`)
    // API 返回 [data, total] 元组
    if (Array.isArray(res)) {
      standards.value = Array.isArray(res[0]) ? res[0] : res
      totalCount.value = res[1] || (Array.isArray(res[0]) ? res[1] : 0)
    } else {
      standards.value = []
      totalCount.value = 0
    }
  } catch (e) {
    ElMessage.error('加载标准失败')
  } finally {
    loading.value = false
  }
}

const selectStandard = async (item) => {
  selectedStandard.value = item
  detailVisible.value = true
  detailLoading.value = true
  detailLimits.value = []
  try {
    const res = await api.get(`/knowledge/standards/${item.id}/limits`)
    detailLimits.value = res.limits || []
  } catch (e) {
    console.error('加载限值失败', e)
  } finally {
    detailLoading.value = false
  }
}

const showAddDialog = () => {
  addVisible.value = true
}

const addStandard = async () => {
  try {
    const payload = {
      ...newStandard.value,
      publish_date: newStandard.value.publish_date
        ? newStandard.value.publish_date.toISOString()
        : null,
    }
    await api.post('/knowledge/standards', payload)
    ElMessage.success('添加成功')
    addVisible.value = false
    loadStandards()
  } catch (e) {
    ElMessage.error('添加失败: ' + (e.response?.data?.detail || e.message))
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadStandards()
})
</script>

<style scoped>
.knowledge-page {
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.meta-text {
  font-size: 12px;
  color: #999;
}

.detail-info {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.info-label {
  font-size: 13px;
  font-weight: 500;
  color: #666;
  margin-bottom: 8px;
}

.info-content {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
}

.limits-section,
.source-section {
  margin-top: 20px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
  margin-bottom: 12px;
}
</style>
