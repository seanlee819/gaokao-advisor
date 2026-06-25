const api = require('../../utils/api')
const app = getApp()

Page({
  data: {
    mode: 'login',
    email: '',
    password: '',
    user: null,
    history: []
  },

  onShow() {
    const user = app.globalData.user
    if (user) {
      this.setData({ user })
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
      this.setData({ user: res.user })
      wx.showToast({ title: mode === 'login' ? '登录成功' : '注册成功', icon: 'success' })
    }).catch(err => {
      wx.showToast({ title: err.detail || '操作失败', icon: 'none' })
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
