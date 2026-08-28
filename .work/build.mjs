import fs from 'node:fs/promises';
import { FileBlob, SpreadsheetFile } from '@oai/artifact-tool';
const input=await FileBlob.load('C:/Users/admin/Desktop/fall-risk-import-template.xlsx');
const wb=await SpreadsheetFile.importXlsx(input);
const sheet=wb.worksheets.getItem('Fall Risk Assessment');
sheet.getRange('A2:N4').values=[
  ['female',62,1,10,0,90,'no','no',2,'no',9,999,'no','no'],
  ['male',68,2,25,1,65,'yes','no',5,'no',14,120,'no','no'],
  ['female',73,4,60,3,35,'yes','yes',9,'yes',24,10,'yes','yes']
];
// Keep numeric fields usable and make the imported records easy to scan.
sheet.getRange('A1:N4').format.borders={preset:'all',style:'thin',color:'#D9D9D9'};
sheet.getRange('A1:N1').format={fill:'#1F4E78',font:{bold:true,color:'#FFFFFF'},wrapText:true};
sheet.getRange('A1:N4').format.autofitColumns();
sheet.getRange('A1:N4').format.autofitRows();
sheet.getRange('B2:B4').format.numberFormat='0';
sheet.getRange('C2:F4').format.numberFormat='0';
sheet.getRange('I2:I4').format.numberFormat='0';
sheet.getRange('K2:L4').format.numberFormat='0';
const outDir='C:/Users/admin/Desktop/Frontend Template/outputs/fall-risk';
await fs.mkdir(outDir,{recursive:true});
const preview=await wb.render({sheetName:'Fall Risk Assessment',range:'A1:N4',scale:1.5,format:'png'});
await fs.writeFile(outDir+'/preview.png',new Uint8Array(await preview.arrayBuffer()));
console.log((await wb.inspect({kind:'table',range:'Fall Risk Assessment!A1:N4',include:'values,formulas',tableMaxRows:10,tableMaxCols:20})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',options:{useRegex:true,maxResults:50}})).ndjson);
const x=await SpreadsheetFile.exportXlsx(wb); await x.save(outDir+'/fall-risk-import-filled.xlsx');
