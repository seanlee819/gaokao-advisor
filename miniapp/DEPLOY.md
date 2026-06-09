# 看金榜 · 微信小程序部署指南

## 一、注册小程序账号（5分钟）

1. 打开 https://mp.weixin.qq.com  → 点「立即注册」→ 选择「小程序」
2. 用未注册过公众号/小程序的邮箱（推荐 QQ 邮箱）
3. 主体类型选「个人」，填身份证信息，微信扫码验证
4. 注册完成后进入后台，记下 **AppID**

## 二、配置服务器域名

在微信小程序后台 → 开发 → 开发管理 → 服务器域名：

```
request合法域名: https://kanjinbang.cn
```

点击保存（一个月可修改5次）。

## 三、下载开发者工具

下载：https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html

## 四、导入项目

1. 打开微信开发者工具 → 「导入项目」
2. 目录选择：`miniapp/`
3. AppID 填入第一步获取的 AppID
4. 项目名称：看金榜

## 五、替换 AppID

编辑 `project.config.json`，将 `YOUR_APPID_HERE` 替换为你的 AppID

## 六、tabBar 图标

需要准备 4 个图标放到 `miniapp/images/`：
- `tab-search.png` (推荐-未选中)
- `tab-search-active.png` (推荐-选中)
- `tab-mine.png` (我的-未选中)  
- `tab-mine-active.png` (我的-选中)

图标规格：81x81px PNG，单色即可。可用 iconfont.cn 生成。

## 七、预览调试

1. 在开发者工具中点击「预览」
2. 手机微信扫码即可体验

## 八、上传审核

1. 开发者工具中点击「上传」
2. 版本号填 1.0.0
3. 在小程序后台 → 版本管理 → 提交审核
4. 审核通过后发布

## 审核注意事项

- 类目选「教育 > 教育信息服务」或「工具 > 信息查询」
- 个人小程序不需要特殊资质
- 确保页面内容无违规（不要有支付、诱导分享等）
