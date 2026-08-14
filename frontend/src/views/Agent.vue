<template>
  <div class="agent-workspace">
    <!-- 顶部状态栏 -->
    <div class="workspace-header">
      <div class="header-left">
        <h2>智能助手工作台</h2>
        <el-tag type="success" size="small" class="status-tag">
          <el-icon><CaretRight /></el-icon> 运行中
        </el-tag>
      </div>
      <div class="header-stats">
        <el-statistic title="交互次数" :value="stats.total_interactions" :precision="0" />
        <el-statistic title="记忆会话" :value="stats.sessions" :precision="0" />
        <el-statistic title="进化轮次" :value="stats.evolution_rounds" :precision="0" />
        <el-statistic title="知识条目" :value="stats.knowledge_entries" :precision="0" />
      </div>
      <div class="header-actions">
        <el-button type="primary" size="small" :loading="evolving" @click="triggerEvolution">
          <el-icon><RefreshLeft /></el-icon> 触发进化
        </el-button>
        <el-button size="small" @click="openCrawlDialog">
          <el-icon><Download /></el-icon> 爬取标准
        </el-button>
        <el-button size="small" @click="clearMemory">
          <el-icon><Delete /></el-icon> 清除记忆
        </el-button>
      </div>
    </div>

    <div class="workspace-body">
      <!-- 左侧：对话区 -->
      <div class="chat-panel">
        <div class="panel-title">对话</div>

        <!-- 模式选择 -->
        <div class="mode-selector">
          <el-radio-group v-model="chatMode" size="small">
            <el-radio-button value="react">思维链</el-radio-button>
            <el-radio-button value="plan">规划模式</el-radio-button>
            <el-radio-button value="simple">简单模式</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 消息列表 -->
        <div class="chat-messages" ref="messageContainer">
          <div v-for="(msg, idx) in messages" :key="idx" class="chat-message" :class="msg.role">
            <div class="chat-avatar">
              <el-icon v-if="msg.role === 'assistant'"><ChatDotRound /></el-icon>
              <el-icon v-else><User /></el-icon>
            </div>
            <div class="chat-content">
              <div class="chat-bubble" v-html="formatMessage(msg.content)"></div>
              <div v-if="msg.steps && msg.steps.length" class="step-trace">
                <el-collapse size="small">
                  <el-collapse-item title="查看推理过程">
                    <div v-for="step in msg.steps" :key="step.step" class="step-item">
                      <el-tag :type="step.type === 'thought' ? '' : 'success'" size="small">
                        {{ step.type === 'thought' ? '思考' : '行动' }}
                      </el-tag>
                      <span class="step-content">{{ step.content || step.tool || '' }}</span>
                      <div v-if="step.observation" class="step-observation">{{ step.observation }}</div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </div>
          <div v-if="loading" class="chat-message assistant">
            <div class="chat-avatar">
              <el-icon class="is-loading"><Loading /></el-icon>
            </div>
            <div class="chat-bubble" style="background: #f0fdf4">
              <el-icon class="is-loading"><Loading /></el-icon> 正在思考...
            </div>
          </div>
        </div>

        <!-- 快捷指令 -->
        <div class="quick-actions">
          <div style="font-size: 12px; color: #999; margin-bottom: 8px">快捷指令</div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px">
            <el-tag
              v-for="cmd in quickCommands"
              :key="cmd.text"
              size="small"
              closable
              style="cursor: pointer"
              @close="removeCommand(cmd)"
              @click="inputMessage = cmd.text"
            >{{ cmd.text }}</el-tag>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="chat-input-area">
          <el-select v-model="selectedSession" size="small" placeholder="选择会话" style="width: 140px" @change="loadSession">
            <el-option v-for="s in sessions" :key="s.session_id" :label="s.session_id" :value="s.session_id" />
            <el-option label="新建会话" value="__new__" />
          </el-select>
          <textarea
            v-model="inputMessage"
            rows="3"
            placeholder="输入问题，如：查询VOCs排放限值、生成巡查报告、分析超标原因..."
            @keydown.enter.ctrl="sendMessage"
            @keydown.enter.shift.prevent
          ></textarea>
          <el-button type="primary" :loading="loading" @click="sendMessage" :disabled="!inputMessage.trim()">
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
        </div>
      </div>

      <!-- 右侧：面板区 -->
      <div class="right-panel">
        <el-tabs v-model="activeTab" type="card">
          <!-- 记忆面板 -->
          <el-tab-pane label="记忆系统" name="memory">
            <div class="tab-content">
              <div class="memory-section">
                <div class="section-title">
                  <el-icon><Collection /></el-icon> 会话列表
                </div>
                <div class="session-list">
                  <div v-for="s in sessions" :key="s.session_id" class="session-item" @click="selectSession(s.session_id)">
                    <div class="session-info">
                      <div class="session-name">{{ s.session_id }}</div>
                      <div class="session-meta">{{ s.turn_count }}轮对话 · {{ s.semantic_count }}条记忆</div>
                    </div>
                    <el-button size="small" type="danger" text @click.stop="deleteSession(s.session_id)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div v-if="sessions.length === 0" class="empty-state">暂无记忆会话</div>
                </div>
              </div>

              <div class="memory-section">
                <div class="section-title">
                  <el-icon><Document /></el-icon> 语义记忆
                </div>
                <div v-if="semanticMemories.length > 0" class="memory-list">
                  <div v-for="(m, i) in semanticMemories" :key="i" class="memory-item">
                    <div class="memory-text">{{ m.text }}</div>
                    <div class="memory-meta">{{ m.created_at }} · 访问{{ m.access_count }}次</div>
                  </div>
                </div>
                <div v-else class="empty-state">暂无语义记忆</div>
              </div>

              <div class="memory-section">
                <div class="section-title">
                  <el-icon><DataLine /></el-icon> 能力指引
                </div>
                <div class="guidance-list">
                  <div v-for="cap in guidance.capabilities" :key="cap.name" class="guidance-item">
                    <el-tag :type="cap.status === 'active' ? 'success' : 'info'" size="small">{{ cap.name }}</el-tag>
                    <div class="guidance-desc">{{ cap.description }}</div>
                  </div>
                </div>
                <div class="suggestions">
                  <div class="section-subtitle">建议操作</div>
                  <div v-for="sug in guidance.suggestions" :key="sug" class="suggestion-item">{{ sug }}</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 进化日志面板 -->
          <el-tab-pane label="进化日志" name="evolution">
            <div class="tab-content">
              <div class="evolution-section">
                <div class="section-title">
                  <el-icon><TrendCharts /></el-icon> 进化历史
                </div>
                <div class="evolution-list">
                  <div v-if="evolutionLogs.length > 0" v-for="(log, i) in evolutionLogs" :key="i" class="evolution-card">
                    <div class="evo-header">
                      <el-tag type="success">第{{ log.round }}轮</el-tag>
                      <span class="evo-time">{{ log.timestamp }}</span>
                    </div>
                    <div class="evo-steps">
                      <div v-for="step in log.steps" :key="step.step" class="evo-step">
                        <el-tag size="small" :type="step.action === 'web_crawl' ? 'warning' : ''">
                          {{ step.action }}
                        </el-tag>
                        <span v-if="step.new_standards !== undefined">新增{{ step.new_standards }}条标准</span>
                        <span v-if="step.gaps_found !== undefined">发现{{ step.gaps_found }}个知识缺口</span>
                      </div>
                    </div>
                    <div class="evo-improvements" v-if="log.improvements">
                      <div v-for="imp in log.improvements" :key="imp" class="evo-imp">{{ imp }}</div>
                    </div>
                  </div>
                  <div v-else class="empty-state">尚未触发进化</div>
                </div>
              </div>

              <div class="evolution-section">
                <div class="section-title">
                  <el-icon><Download /></el-icon> 爬取历史
                </div>
                <div class="crawl-list">
                  <div v-if="crawlHistory.length > 0" v-for="log in crawlHistory" :key="log.id" class="crawl-item">
                    <div class="crawl-title">{{ log.title || log.url }}</div>
                    <div class="crawl-meta">{{ log.source }} · 新增{{ log.new_standards }}条 · {{ log.crawled_at }}</div>
                    <el-tag :type="log.status === 'success' ? 'success' : 'danger'" size="small">{{ log.status }}</el-tag>
                  </div>
                  <div v-else class="empty-state">暂无爬取记录</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- 知识库统计面板 -->
          <el-tab-pane label="知识库" name="knowledge">
            <div class="tab-content">
              <div class="knowledge-stats">
                <div class="ks-item">
                  <div class="ks-value">{{ knowledgeStats.standards }}</div>
                  <div class="ks-label">环保标准</div>
                </div>
                <div class="ks-item">
                  <div class="ks-value">{{ knowledgeStats.factors }}</div>
                  <div class="ks-label">污染因子</div>
                </div>
                <div class="ks-item">
                  <div class="ks-value">{{ knowledgeStats.limits }}</div>
                  <div class="ks-label">排放限值</div>
                </div>
                <div class="ks-item">
                  <div class="ks-value">{{ knowledgeStats.news }}</div>
                  <div class="ks-label">环保资讯</div>
                </div>
                <div class="ks-item">
                  <div class="ks-value">{{ knowledgeStats.devices }}</div>
                  <div class="ks-label">接入设备</div>
                </div>
                <div class="ks-item">
                  <div class="ks-value">{{ knowledgeStats.enterprise_standards }}</div>
                  <div class="ks-label">企业标准</div>
                </div>
              </div>
              <div class="expand-section">
                <el-button type="primary" size="small" @click="openCrawlDialog">
                  <el-icon><Download /></el-icon> 从网络采集标准
                </el-button>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 爬取对话框 -->
    <el-dialog v-model="crawlDialogVisible" title="网络标准采集" width="500px">
      <el-form label-width="80px">
        <el-form-item label="爬取来源">
          <el-select v-model="crawlSource" style="width: 100%">
            <el-option label="全部来源" value="auto" />
            <el-option label="生态环境部" value="mee" />
            <el-option label="国家标准" value="std" />
          </el-select>
        </el-form-item>
        <el-form-item label="爬取数量">
          <el-input-number v-model="crawlLimit" :min="5" :max="50" :step="5" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="crawlDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="crawling" @click="doCrawl">开始爬取</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

// === 对话持久化 ===
const STORAGE_KEY = 'agent_chat_history'
const SESSION_KEY = 'agent_chat_session'
const MODE_KEY = 'agent_chat_mode'

// 从 localStorage 加载历史对话
const loadMessagesFromStorage = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed
      }
    }
  } catch (e) { console.error('加载对话历史失败', e) }
  return [{
    role: 'assistant',
    content: '你好！我是化工环保智能助手 🌿\n\n我具备记忆功能和自进化能力，可以帮你：\n\n📊 查询排放限值 — 如"VOCs排放标准是多少"\n📝 生成环保报告 — 如"帮我生成日常巡查报告"\n🔔 超标预警分析 — 如"最近有什么超标记录"\n📰 环保资讯 — 如"最近有什么环保新闻"\n🔮 趋势预测 — 如"预测未来排放趋势"\n🕷 网络爬取 — 如"采集最新VOCs标准"\n\n💡 试试对我说：查询GB31570的VOCs排放限值',
  }]
}

// 保存对话到 localStorage
const saveMessagesToStorage = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value))
  } catch (e) { console.error('保存对话历史失败', e) }
}

// 状态
const messages = ref(loadMessagesFromStorage())

const inputMessage = ref('')
const loading = ref(false)
const evolving = ref(false)
const crawling = ref(false)
const chatMode = ref(localStorage.getItem(MODE_KEY) || 'react')
const selectedSession = ref(localStorage.getItem(SESSION_KEY) || 'default')
const activeTab = ref('memory')
const messageContainer = ref(null)
const crawlDialogVisible = ref(false)
const crawlSource = ref('auto')
const crawlLimit = ref(20)

// 监听消息变化，自动保存
watch(messages, () => {
  saveMessagesToStorage()
}, { deep: true })

// 监听会话和模式变化，自动保存
watch(selectedSession, (val) => {
  localStorage.setItem(SESSION_KEY, val)
})
watch(chatMode, (val) => {
  localStorage.setItem(MODE_KEY, val)
})

// 数据
const stats = ref({ total: 0, sessions: 0, tool_calls: 0, knowledge_entries: 0, evolution_rounds: 0 })
const sessions = ref([])
const semanticMemories = ref([])
const guidance = ref({ capabilities: [], suggestions: [] })
const evolutionLogs = ref([])
const crawlHistory = ref([])
const knowledgeStats = ref({ standards: 0, factors: 0, limits: 0, news: 0, devices: 0, enterprise_standards: 0 })

const quickCommands = ref([
  { text: '查询VOCs排放限值' },
  { text: '帮我生成日常巡查报告' },
  { text: '最近有什么环保新闻' },
  { text: '分析DA001排放趋势' },
  { text: '采集最新环保标准' },
  { text: '对比GB31570和GB16297的VOCs限值' },
])

// 加载数据
const loadStats = async () => {
  try {
    const res = await api.get('/agent/status')
    stats.value = res
  } catch (e) { console.error(e) }
}

const loadSessions = async () => {
  try {
    const res = await api.get('/agent/memory/sessions')
    sessions.value = res || []
  } catch (e) { console.error(e) }
}

const loadKnowledgeStats = async () => {
  try {
    const res = await api.get('/knowledge/stats')
    knowledgeStats.value = res
  } catch (e) { console.error(e) }
}

const loadGuidance = async () => {
  try {
    const res = await api.get('/agent/guidance')
    guidance.value = res
  } catch (e) { console.error(e) }
}

const loadCrawlHistory = async () => {
  try {
    const res = await api.get('/agent/crawl/history')
    crawlHistory.value = res || []
  } catch (e) { console.error(e) }
}

const loadSessionMemories = async (sessionId) => {
  try {
    const res = await api.get(`/agent/memory/sessions/${sessionId}`)
    semanticMemories.value = res.semantic_memories || []
  } catch (e) { console.error(e) }
}

// 操作
const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || loading.value) return

  const sessionId = selectedSession.value === '__new__' ? `session_${Date.now()}` : selectedSession.value
  if (selectedSession.value === '__new__') {
    selectedSession.value = sessionId
    await loadSessions()
  }

  messages.value.push({ role: 'user', content: text })
  inputMessage.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await api.post('/agent/chat', { message: text, session_id: sessionId, mode: chatMode.value })
    messages.value.push({
      role: 'assistant',
      content: res.reply || '暂无回复',
      steps: res.steps || [],
    })
    await loadStats()
    scrollToBottom()
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，处理请求时出现错误。请稍后重试。',
    })
    ElMessage.error('请求失败')
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

const triggerEvolution = async () => {
  evolving.value = true
  try {
    const res = await api.post('/agent/evolve')
    evolutionLogs.value.unshift(res)
    ElMessage.success(`进化完成！新增 ${res.new_knowledge} 条知识`)
    await loadStats()
  } catch (e) {
    ElMessage.error('进化失败')
  } finally {
    evolving.value = false
  }
}

const doCrawl = async () => {
  crawling.value = true
  try {
    const res = await api.post('/agent/crawl/standards', { source: crawlSource.value, limit: crawlLimit.value })
    ElMessage.success(`爬取完成，新增 ${res.new_standards || 0} 条标准`)
    crawlDialogVisible.value = false
    await loadCrawlHistory()
    await loadKnowledgeStats()
    await loadStats()
  } catch (e) {
    ElMessage.error('爬取失败')
  } finally {
    crawling.value = false
  }
}

const openCrawlDialog = () => { crawlDialogVisible.value = true }

const selectSession = async (sessionId) => {
  selectedSession.value = sessionId
  await loadSessionMemories(sessionId)
  await loadStats()
}

const loadSession = async () => {
  if (selectedSession.value && selectedSession.value !== '__new__') {
    await loadSessionMemories(selectedSession.value)
  }
}

const deleteSession = async (sessionId) => {
  try {
    await ElMessageBox.confirm(`确定清除会话 "${sessionId}" 的记忆吗？`, '确认', { type: 'warning' })
    await api.delete(`/agent/memory/sessions/${sessionId}`)
    await loadSessions()
    ElMessage.success('已清除')
    if (selectedSession.value === sessionId) {
      semanticMemories.value = []
    }
  } catch (e) {}
}

const clearMemory = async () => {
  try {
    await ElMessageBox.confirm('确定清除所有记忆吗？此操作不可恢复。', '警告', { type: 'warning' })
    await api.post('/agent/memory/clear-all')
    sessions.value = []
    semanticMemories.value = []
    messages.value = [{
      role: 'assistant',
      content: '你好！我是化工环保智能助手 🌿\n\n记忆已清除，让我们重新开始吧！',
    }]
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(SESSION_KEY)
    selectedSession.value = 'default'
    ElMessage.success('已清除所有记忆')
    await loadStats()
  } catch (e) {}
}

const removeCommand = (cmd) => {
  quickCommands.value = quickCommands.value.filter(c => c !== cmd)
}

const formatMessage = (content) => {
  if (!content) return ''
  return content
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  await Promise.all([loadStats(), loadSessions(), loadKnowledgeStats(), loadGuidance(), loadEvolutionLogs()])
  scrollToBottom()
})
</script>

<style scoped>
.agent-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 104px);
}

.workspace-header {
  background: #fff;
  border-radius: 12px;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.status-tag {
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-stats {
  display: flex;
  gap: 24px;
}

.header-stats :deep(.el-statistic) {
  margin: 0;
}

.header-stats :deep(.el-statistic__content) {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.workspace-body {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* 左侧对话区 */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  min-width: 0;
}

.panel-title {
  padding: 16px 20px 12px;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  border-bottom: 1px solid #f0f0f0;
}

.mode-selector {
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.chat-message {
  display: flex;
  margin-bottom: 16px;
  gap: 12px;
  align-items: flex-start;
}

.chat-message.user {
  flex-direction: row-reverse;
}

.chat-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 16px;
  background: linear-gradient(135deg, #4ade80, #22c55e);
  color: #fff;
}

.chat-message.user .chat-avatar {
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
}

.chat-content {
  max-width: 75%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.chat-message.assistant .chat-bubble {
  background: #f0fdf4;
  color: #1a1a1a;
  border-top-left-radius: 4px;
}

.chat-message.user .chat-bubble {
  background: #3b82f6;
  color: #fff;
  border-top-right-radius: 4px;
}

.step-trace {
  font-size: 12px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 4px 0;
  flex-wrap: wrap;
}

.step-content {
  color: #666;
  flex: 1;
}

.step-observation {
  color: #888;
  font-size: 11px;
  margin-left: 60px;
  max-width: 100%;
  word-break: break-all;
}

.quick-actions {
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
}

.chat-input-area {
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.chat-input-area textarea {
  flex: 1;
  resize: none;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.2s;
  min-height: 60px;
}

.chat-input-area textarea:focus {
  border-color: #4ade80;
}

/* 右侧面板 */
.right-panel {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.right-panel :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 12px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.tab-content {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.memory-section, .evolution-section, .knowledge-section {
  margin-bottom: 20px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-subtitle {
  font-size: 12px;
  color: #999;
  margin-bottom: 8px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #f8faf9;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.session-item:hover {
  background: #f0fdf4;
}

.session-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a1a;
}

.session-meta {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.memory-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-item {
  padding: 10px 12px;
  background: #f8faf9;
  border-radius: 8px;
  border-left: 3px solid #4ade80;
}

.memory-text {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}

.memory-meta {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}

.guidance-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guidance-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.guidance-desc {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  flex: 1;
}

.suggestions {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.suggestion-item {
  font-size: 12px;
  color: #666;
  padding: 4px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.suggestion-item::before {
  content: "→";
  color: #4ade80;
}

/* 进化日志 */
.evolution-card {
  padding: 12px;
  background: #f8faf9;
  border-radius: 8px;
  margin-bottom: 10px;
  border: 1px solid #e8f5e9;
}

.evo-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.evo-time {
  font-size: 11px;
  color: #999;
}

.evo-steps {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.evo-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #555;
}

.evo-improvements {
  border-top: 1px solid #e0e0e0;
  padding-top: 8px;
}

.evo-imp {
  font-size: 12px;
  color: #4ade80;
  padding: 2px 0;
}

/* 爬取历史 */
.crawl-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.crawl-item {
  padding: 10px 12px;
  background: #f8faf9;
  border-radius: 8px;
}

.crawl-title {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a1a;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crawl-meta {
  font-size: 11px;
  color: #999;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 知识库统计 */
.knowledge-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.ks-item {
  text-align: center;
  padding: 16px 8px;
  background: #f8faf9;
  border-radius: 10px;
  border: 1px solid #e8f5e9;
}

.ks-value {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
}

.ks-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.expand-section {
  text-align: center;
  padding: 12px;
  border-top: 1px solid #f0f0f0;
}

.empty-state {
  text-align: center;
  color: #bbb;
  font-size: 13px;
  padding: 20px 0;
}
</style>
