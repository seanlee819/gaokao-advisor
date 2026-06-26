# 高考志愿推荐 — 微信小程序前端

## 项目结构
```
miniapp/
├── app.js          # 全局配置
├── app.json        # 页面路由
├── app.wxss        # 全局样式
├── pages/
│   ├── index/      # 首页(查询输入)
│   ├── result/     # 推荐结果(冲稳保)
│   └── plan/       # 志愿方案
└── utils/
    └── api.js      # API 封装
```

## 1. utils/api.js — API 封装

```javascript
const BASE = 'https://your-domain.com/api';

const request = (path, data = {}, method = 'GET') => {
  return new Promise((resolve, reject) => {
    wx.request({
      url: BASE + path,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      success: res => resolve(res.data),
      fail: err => reject(err)
    });
  });
};

module.exports = {
  quickRecommend: (score, rank, province, category) =>
    request(`/miniapp/quick?score=${score}&rank=${rank}&province=${province}&category=${category}`),
  
  login: (email, password) =>
    request('/login', { email, password }, 'POST'),
  
  register: (email, password) =>
    request('/register', { email, password }, 'POST'),
  
  recommend: (params, token) =>
    request(`/recommend?token=${token}`, params, 'POST'),
  
  getProvinces: () => request('/provinces'),
  getMajorCategories: () => request('/major_categories'),
};
```

## 2. pages/index/index.wxml — 查询首页

```xml
<view class="container">
  <view class="header">
    <text class="title">🎓 高考志愿助手</text>
    <text class="subtitle">位次法+线差法 · 冲稳保推荐</text>
  </view>

  <view class="form">
    <picker mode="selector" range="{{provinces}}" bindchange="onProvinceChange">
      <view class="picker">{{province || '选择省份'}}</view>
    </picker>

    <picker mode="selector" range="{{categories}}" bindchange="onCategoryChange">
      <view class="picker">{{category || '选择科类'}}</view>
    </picker>

    <view class="input-row">
      <input class="input" type="number" placeholder="分数(0-750)" bindinput="onScoreInput" value="{{score}}"/>
      <input class="input" type="number" placeholder="全省位次" bindinput="onRankInput" value="{{rank}}"/>
    </view>

    <button class="btn-primary" bindtap="onSearch">🔍 开始推荐</button>
    <button class="btn-secondary" bindtap="onQuickSearch">🚀 快速查看(免登录)</button>
  </view>

  <view class="disclaimer">
    ⚠️ 数据仅供参考，请以官方发布为准
  </view>
</view>
```

## 3. pages/index/index.js

```javascript
const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    provinces: [], categories: ['理科','文科','物理类','历史类','综合'],
    province: '河南', category: '理科', score: '', rank: ''
  },
  onLoad() {
    api.getProvinces().then(res => this.setData({ provinces: res.provinces }));
  },
  onProvinceChange(e) { this.setData({ province: this.data.provinces[e.detail.value] }); },
  onCategoryChange(e) { this.setData({ category: this.data.categories[e.detail.value] }); },
  onScoreInput(e) { this.setData({ score: e.detail.value }); },
  onRankInput(e) { this.setData({ rank: e.detail.value }); },
  
  onQuickSearch() {
    wx.showLoading({ title: '分析中...' });
    api.quickRecommend(this.data.score, this.data.rank, this.data.province, this.data.category)
      .then(res => {
        wx.hideLoading();
        app.globalData.result = res;
        wx.navigateTo({ url: '/pages/result/result' });
      })
      .catch(err => { wx.hideLoading(); wx.showToast({ title: '查询失败', icon: 'none' }); });
  },
  
  onSearch() {
    // 已登录用户使用完整版
    const token = app.globalData.token;
    if (!token) {
      wx.showModal({
        title: '登录后解锁更多',
        content: '登录后可查看完整推荐和专业详情',
        success: r => { if (r.confirm) wx.navigateTo({ url: '/pages/login/login' }); }
      });
      return;
    }
    wx.showLoading({ title: '分析中...' });
    api.recommend({
      score: Number(this.data.score), rank: Number(this.data.rank),
      province: this.data.province, category: this.data.category
    }, token)
      .then(res => {
        wx.hideLoading();
        app.globalData.result = res;
        wx.navigateTo({ url: '/pages/result/result' });
      });
  }
});
```

## 4. pages/result/result.wxml — 结果页

```xml
<view class="container">
  <view class="info-bar">
    <text>{{info.score}}分 · {{info.rank}}位 · {{info.batch}}</text>
  </view>

  <view class="tabs">
    <view class="tab {{activeTab==='冲'?'active':''}}" bindtap="switchTab" data-tab="冲">
      🔴 冲 {{summary['冲']}}所
    </view>
    <view class="tab {{activeTab==='稳'?'active':''}}" bindtap="switchTab" data-tab="稳">
      🔵 稳 {{summary['稳']}}所
    </view>
    <view class="tab {{activeTab==='保'?'active':''}}" bindtap="switchTab" data-tab="保">
      🟢 保 {{summary['保']}}所
    </view>
  </view>

  <view class="school-list">
    <block wx:for="{{schools}}" wx:key="name">
      <view class="school-card">
        <view class="school-name">{{item.name}} <text class="level">{{item.level}}</text></view>
        <view class="school-info">{{item.city}} · 均分{{item.uni_avg_score}} · 概率{{item.probability}}%</view>
      </view>
    </block>
  </view>

  <view class="disclaimer">
    ⚠️ 以上推荐基于历史数据估算，仅供参考
  </view>
</view>
```

## 5. app.json

```json
{
  "pages": [
    "pages/index/index",
    "pages/result/result",
    "pages/plan/plan",
    "pages/login/login"
  ],
  "window": {
    "navigationBarTitleText": "高考志愿助手",
    "navigationBarBackgroundColor": "#1a73e8",
    "navigationBarTextStyle": "white"
  }
}
```
