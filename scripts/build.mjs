import {copyFileSync,mkdirSync} from 'node:fs';
mkdirSync('dist/web',{recursive:true});
copyFileSync('index.html','dist/index.html');
copyFileSync('web/style.css','dist/web/style.css');
copyFileSync('web/v2-style.css','dist/web/v2-style.css');
copyFileSync('web/legacy-style.css','dist/web/legacy-style.css');

copyFileSync('web/v3-style.css','dist/web/v3-style.css');
