const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    mode: 'login',
    email: '',
    password: '',
    user: null,
    limits: { max_queries: 3 },
    tierName: '免费版',
    showPayModal: false,
    payTier: '',
    payTierName: '',
    payPrice: '',
    completePrice: '29.9',
    history: []
  },

  onShow() {
    const user = app.globalData.user
    if (user) {
      this.loadUserData(user)
    }
    this.loadHistory()
  },

  onEmailInput(e) { this.setData({ email: e.detail.value }) },
  onPwdInput(e) { this.setData({ password: e.detail.value }) },

  onSwitchMode() {
    this.setData({ mode: this.data.mode === 'login' ? 'register' : 'login' })
  },

  onLogin() {
    const { email, password, mode } = this.data
    if (!email || !password) {
      wx.showToast({ title: '请输入邮箱和密码', icon: 'none' })
      return
    }
    if (password.length < 6) {
      wx.showToast({ title: '密码至少6位', icon: 'none' })
      return
    }

    const fn = mode === 'login' ? api.login : api.register
    fn(email, password).then(res => {
      app.globalData.token = res.token
      app.globalData.user = res.user
      wx.setStorageSync('token', res.token)
      this.loadUserData(res.user)
      wx.showToast({ title: mode === 'login' ? '登录成功' : '注册成功', icon: 'success' })
    }).catch(err => {
      wx.showToast({ title: err.detail || '操作失败', icon: 'none' })
    })
  },

  loadUserData(user) {
    const tierNames = { free: '免费版', enhanced: '增强版', complete: '完全版' }
    const limitsMap = {
      free: { max_queries: 3 },
      enhanced: { max_queries: 30 },
      complete: { max_queries: 9999 }
    }
    this.setData({
      user,
      tierName: tierNames[user.tier] || '免费版',
      limits: limitsMap[user.tier] || { max_queries: 3 },
      completePrice: user.tier === 'free' ? '29.9' : '20'
    })
  },

  showUpgrade(e) {
    const tier = e.currentTarget.dataset.tier
    const price = e.currentTarget.dataset.price
    const names = { enhanced: '增强版', complete: '完全版' }
    this.setData({
      showPayModal: true,
      payTier: tier,
      payTierName: names[tier],
      payPrice: price
    })
  },

  closeModal() {
    this.setData({ showPayModal: false })
  },

  copyEmail() {
    wx.setClipboardData({
      data: this.data.user.email,
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    })
  },

  copyWxid() {
    wx.setClipboardData({
      data: 'seanlee819',
      success: () => wx.showToast({ title: '已复制', icon: 'success' })
    })
  },

  onLogout() {
    app.globalData.token = ''
    app.globalData.user = null
    wx.removeStorageSync('token')
    this.setData({ user: null })
  },

  loadHistory() {
    this.setData({
      history: wx.getStorageSync('query_history') || []
    })
  },

  revisit(e) {
    const item = this.data.history[e.currentTarget.dataset.index]
    if (item && item.data) {
      wx.navigateTo({
        url: `/pages/result/result?data=${encodeURIComponent(item.data)}`
      })
    }
  }
})
