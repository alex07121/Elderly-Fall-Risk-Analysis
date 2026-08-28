import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const input=await FileBlob.load('C:/Users/admin/Desktop/fall-risk-import-template.xlsx');
const wb=await SpreadsheetFile.importXlsx(input);
console.log((await wb.inspect({kind:'workbook,sheet,table,region',maxChars:10000,tableMaxRows:20,tableMaxCols:20})).ndjson);
for (const s of wb.worksheets.items){ const p=await wb.render({sheetName:s.name,autoCrop:'all',scale:1,format:'png'}); await (await import('node:fs/promises')).writeFile('.work/'+s.name+'.png',new Uint8Array(await p.arrayBuffer())); }
