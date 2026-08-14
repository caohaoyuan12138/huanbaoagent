<template>
  <div>
    <div class="card" style="margin-bottom: 16px">
      <div class="card-header">
        <h3>环保资讯</h3>
        <div style="display: flex; gap: 8px; align-items: center">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索资讯..."
            clearable
            style="width: 200px"
            @input="handleSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-select v-model="filterCategory" size="small" style="width: 120px" @change="loadNews">
            <el-option label="全部" value="" />
            <el-option label="政策法规" value="policy" />
            <el-option label="行业标准" value="standard" />
            <el-option label="行业动态" value="industry" />
            <el-option label="环保新闻" value="news" />
          </el-select>
        </div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col
        v-for="item in newsList"
        :key="item.id"
        :span="8"
      >
        <div class="news-card" @click="openNews(item)">
          <div class="news-title">{{ item.title }}</div>
          <div class="news-summary">{{ item.summary }}</div>
          <div class="news-meta">
            <div class="news-tags">
              <el-tag v-for="tag in item.tags" :key="tag" size="small" type="info" style="margin-right: 4px">{{ tag }}</el-tag>
            </div>
            <span>{{ item.source }}</span>
          </div>
          <div style="font-size: 11px; color: #bbb; margin-top: 8px">
            {{ formatDate(item.published_at) }}
          </div>
        </div>
      </el-col>
    </el-row>

    <div style="text-align: center; margin-top: 24px">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="12"
        :total="totalNews"
        layout="prev, pager, next"
        @current-change="loadNews"
      />
    </div>

    <!-- 新闻详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detailItem?.title" width="700px" top="5vh">
      <div v-if="detailItem">
        <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap">
          <el-tag :type="categoryType(detailItem.category)" size="small">{{ categoryLabel(detailItem.category) }}</el-tag>
          <el-tag v-for="tag in detailItem.tags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
        </div>
        <div style="font-size: 12px; color: #999; margin-bottom: 16px">
          来源：{{ detailItem.source }} &nbsp;|&nbsp; 时间：{{ formatDate(detailItem.published_at) }}
        </div>
        <div style="font-size: 14px; line-height: 2; color: #333; min-height: 100px">
          {{ detailItem.content || detailItem.summary }}
        </div>
        <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #f0f0f0">
          <el-link v-if="detailItem.url && isSafeUrl(detailItem.url)" :href="detailItem.url" target="_blank" type="primary">
            <el-icon><Link /></el-icon> 查看原文链接
          </el-link>
          <span v-else style="font-size: 13px; color: #999">暂无原文链接</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'

const route = useRoute()
const newsList = ref([])
const totalNews = ref(0)
const searchKeyword = ref('')
const filterCategory = ref('')
const currentPage = ref(1)
const detailVisible = ref(false)
const detailItem = ref(null)

const categoryLabel = (cat) => {
  const labels = { policy: '政策法规', standard: '行业标准', industry: '行业动态', news: '环保新闻' }
  return labels[cat] || cat
}

const categoryType = (cat) => {
  const types = { policy: 'danger', standard: 'warning', industry: '', news: 'info' }
  return types[cat] || ''
}

const handleSearch = () => {
  currentPage.value = 1
  loadNews()
}

const loadNews = async () => {
  try {
    const params = {
      limit: 12,
      offset: (currentPage.value - 1) * 12,
    }
    if (filterCategory.value) params.category = filterCategory.value
    if (searchKeyword.value) params.keyword = searchKeyword.value

    const res = await api.get('/news/news', { params })
    newsList.value = res
    totalNews.value = Math.max(res.length, totalNews.value)
    if (currentPage.value === 1 && !totalNewsCached.value) {
      totalNews.value = await getTotalNewsCount(filterCategory.value, searchKeyword.value)
      totalNewsCached.value = true
    }
  } catch (e) {
    console.error('加载新闻失败', e)
  }
}

const totalNewsCached = ref(false)
const getTotalNewsCount = async (category, keyword) => {
  try {
    const params = { limit: 1, offset: 0 }
    if (category) params.category = category
    if (keyword) params.keyword = keyword
    const res = await api.get('/news/news', { params })
    return res.length || 0
  } catch { return 0 }
}

const openNews = async (item) => {
  try {
    const res = await api.get(`/news/news/${item.id}`)
    detailItem.value = res
    detailVisible.value = true
  } catch (e) {
    detailItem.value = item
    detailVisible.value = true
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString('zh-CN')
}

// URL安全检查 - 仅允许政府官网域名
const isSafeUrl = (url) => {
  if (!url || typeof url !== 'string') return false
  const urlLower = url.toLowerCase()
  // 拦截可疑关键词
  const suspicious = ['sex', 'porn', 'adult', 'xxx', 'gamble', 'casino', '色情', '赌博']
  if (suspicious.some(k => urlLower.includes(k))) return false
  // 仅允许政府官网域名
  const allowedDomains = ['mee.gov.cn', 'gov.cn', 'nhc.gov.cn', 'ndrc.gov.cn', 'miit.gov.cn', 'mnr.gov.cn']
  return allowedDomains.some(d => urlLower.includes(d))
}

watch(filterCategory, () => {
  currentPage.value = 1
  loadNews()
})

watch(() => route.query.id, (id) => {
  if (id) {
    const item = newsList.value.find(n => n.id === Number(id))
    if (item) openNews(item)
  }
})

onMounted(() => {
  loadNews()
  if (route.query.id) {
    setTimeout(() => {
      const item = newsList.value.find(n => n.id === Number(route.query.id))
      if (item) openNews(item)
    }, 500)
  }
})
</script>
