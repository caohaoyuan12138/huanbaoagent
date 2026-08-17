<template>
  <div>
    <el-row :gutter="16">
      <!-- 设备读数导入 -->
      <el-col :span="12">
        <div class="card">
          <div class="card-header">
            <h3><el-icon><Upload /></el-icon> 导入设备监测数据</h3>
          </div>
          <div class="card-body">
            <el-alert type="info" :closable="false" style="margin-bottom: 16px">
              <template #title>
                支持的列：<code>device_id</code>、<code>factor</code>、<code>value</code>、<code>unit</code>、<code>timestamp</code>
              </template>
            </el-alert>
            <el-upload
              ref="uploadReadings"
              :auto-upload="false"
              :on-change="handleReadingFile"
              drag
              :limit="1"
              accept=".csv,.xlsx,.xls"
            >
              <el-icon :size="48" style="color: #4ade80"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽文件到此处 或 <em>点击上传</em></div>
              <template #tip>
                <div style="color: #999; font-size: 12px; margin-top: 8px">支持 CSV、Excel (.xlsx/.xls)，单文件最大 10MB</div>
              </template>
            </el-upload>
            <div v-if="readingResult" style="margin-top: 16px">
              <el-alert
                :type="readingResult.error_count > 0 ? 'warning' : 'success'"
                :title="`导入完成：成功 ${readingResult.imported} 条，失败 ${readingResult.error_count} 条`"
                :closable="false"
              />
              <div v-if="readingResult.errors?.length" style="margin-top: 8px; max-height: 150px; overflow-y: auto">
                <div v-for="(err, i) in readingResult.errors" :key="i" style="font-size: 12px; color: #f56c6c; padding: 2px 0">
                  {{ err }}
                </div>
              </div>
            </div>
            <el-button type="primary" style="margin-top: 12px" :loading="readingUploading" @click="uploadReadings">
              <el-icon><Upload /></el-icon> 开始导入
            </el-button>
          </div>
        </div>
      </el-col>

      <!-- 标准数据导入 -->
      <el-col :span="12">
        <div class="card">
          <div class="card-header">
            <h3><el-icon><Document /></el-icon> 导入环保标准</h3>
          </div>
          <div class="card-body">
            <el-alert type="info" :closable="false" style="margin-bottom: 16px">
              <template #title>
                支持的列：<code>title</code>、<code>standard_type</code>、<code>pollution_factors</code>、<code>publish_date</code>（可选：industry, category, sub_category, source_url, status）
              </template>
            </el-alert>
            <el-upload
              ref="uploadStandards"
              :auto-upload="false"
              :on-change="handleStandardFile"
              drag
              :limit="1"
              accept=".csv,.xlsx,.xls"
            >
              <el-icon :size="48" style="color: #60a5fa"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽文件到此处 或 <em>点击上传</em></div>
              <template #tip>
                <div style="color: #999; font-size: 12px; margin-top: 8px">支持 CSV、Excel (.xlsx/.xls)，单文件最大 10MB</div>
              </template>
            </el-upload>
            <div v-if="standardResult" style="margin-top: 16px">
              <el-alert
                :type="standardResult.error_count > 0 ? 'warning' : 'success'"
                :title="`导入完成：成功 ${standardResult.imported} 条，失败 ${standardResult.error_count} 条`"
                :closable="false"
              />
              <div v-if="standardResult.errors?.length" style="margin-top: 8px; max-height: 150px; overflow-y: auto">
                <div v-for="(err, i) in standardResult.errors" :key="i" style="font-size: 12px; color: #f56c6c; padding: 2px 0">
                  {{ err }}
                </div>
              </div>
            </div>
            <el-button type="primary" style="margin-top: 12px" :loading="standardUploading" @click="uploadStandardsAction">
              <el-icon><Upload /></el-icon> 开始导入
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 下载模板 -->
    <div class="card" style="margin-top: 16px">
      <div class="card-header">
        <h3><el-icon><Download /></el-icon> 导入模板下载</h3>
      </div>
      <div class="card-body">
        <el-row :gutter="16">
          <el-col :span="8">
            <div style="border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; text-align: center">
              <el-icon :size="32" style="color: #4ade80; margin-bottom: 8px"><Document /></el-icon>
              <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px">设备读数模板</div>
              <div style="font-size: 12px; color: #999; margin-bottom: 12px">CSV格式，包含device_id, factor, value, unit, timestamp</div>
              <el-button size="small" type="primary" @click="downloadReadingTemplate">
                <el-icon><Download /></el-icon> 下载模板
              </el-button>
            </div>
          </el-col>
          <el-col :span="8">
            <div style="border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; text-align: center">
              <el-icon :size="32" style="color: #60a5fa; margin-bottom: 8px"><Collection /></el-icon>
              <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px">标准数据模板</div>
              <div style="font-size: 12px; color: #999; margin-bottom: 12px">CSV格式，包含title, standard_type, pollution_factors, publish_date</div>
              <el-button size="small" type="primary" @click="downloadStandardTemplate">
                <el-icon><Download /></el-icon> 下载模板
              </el-button>
            </div>
          </el-col>
          <el-col :span="8">
            <div style="border: 1px solid #e4e7ed; border-radius: 8px; padding: 16px; text-align: center">
              <el-icon :size="32" style="color: #f59e0b; margin-bottom: 8px"><Sheet /></el-icon>
              <div style="font-size: 14px; font-weight: 500; margin-bottom: 8px">Excel批量导入</div>
              <div style="font-size: 12px; color: #999; margin-bottom: 12px">支持 .xlsx/.xls 格式，列名与CSV模板相同</div>
              <el-button size="small" disabled type="info">
                暂不支持（请改用CSV）
              </el-button>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Sheet } from '@element-plus/icons-vue'
import api from '@/api'

const uploadReadings = ref(null)
const uploadStandards = ref(null)
const readingResult = ref(null)
const standardResult = ref(null)
const readingUploading = ref(false)
const standardUploading = ref(false)
let readingFile = ref(null)
let standardFile = ref(null)

const handleReadingFile = (file) => {
  readingFile.value = file.raw
}

const handleStandardFile = (file) => {
  standardFile.value = file.raw
}

const uploadReadingsAction = async () => {
  if (!readingFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  readingUploading.value = true
  readingResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', readingFile.value)
    const res = await api.post('/import/device-readings', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    readingResult.value = res
    ElMessage.success(`成功导入 ${res.imported} 条数据`)
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    readingUploading.value = false
  }
}

const uploadStandardsAction = async () => {
  if (!standardFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  standardUploading.value = true
  standardResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', standardFile.value)
    const res = await api.post('/import/standards', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    standardResult.value = res
    ElMessage.success(`成功导入 ${res.imported} 条标准`)
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    standardUploading.value = false
  }
}

const downloadReadingTemplate = () => {
  const csv = 'device_id,factor,value,unit,timestamp\n1,VOCs,45.2,mg/m3,2026-08-14 10:00:00\n1,COD,38.5,mg/L,2026-08-14 10:00:00\n2,VOCs,52.1,mg/m3,2026-08-14 10:00:00'
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'device_readings_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

const downloadStandardTemplate = () => {
  const csv = 'title,standard_type,pollution_factors,publish_date,industry,category,source_url\nGB 8978-1996 污水综合排放标准,综合标准,"COD,NH3-N,VOCs",1996-12-31,general,废水,https://example.com'
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'standards_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// Import.vue handles upload via el-upload ref, buttons call handler functions directly
</script>

<style scoped>
.el-upload-dragger {
  width: 100% !important;
}
</style>
