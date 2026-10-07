const {defineConfig}=require('@playwright/test');
module.exports=defineConfig({testDir:'./e2e',timeout:60000,use:{baseURL:'http://127.0.0.1:5173',headless:true,viewport:{width:1440,height:1100}},workers:1});
