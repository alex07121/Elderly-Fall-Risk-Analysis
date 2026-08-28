import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const src='C:/Users/admin/Desktop/Frontend Template/outputs/fall-risk/fall-risk-import-filled.xlsx';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(src));
const s=wb.worksheets.getItem('Fall Risk Assessment');
s.getRange('A2:N4').values=[
 ['Female',62,1,10,0,9,'No',0,2,'No',9,365,'No','No'],
 ['Male',68,2,25,1,6,'Yes',1,5,'No',14,120,'No','No'],
 ['Female',73,4,60,3,2,'Yes',2,9,'Yes',24,10,'Yes','Yes']
];
const outDir='C:/Users/admin/Desktop/Frontend Template/outputs/fall-risk';
const p=await wb.render({sheetName:'Fall Risk Assessment',range:'A1:N4',scale:1.5,format:'png'});
await fs.writeFile(outDir+'/preview-corrected.png',new Uint8Array(await p.arrayBuffer()));
const x=await SpreadsheetFile.exportXlsx(wb); await x.save(outDir+'/fall-risk-import-filled.xlsx');
console.log((await wb.inspect({kind:'table',range:'Fall Risk Assessment!A1:N4',include:'values,formulas',tableMaxRows:10,tableMaxCols:20})).ndjson);
