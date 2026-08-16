
((root,factory)=>{const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.EGSCanonicalV4=api;})(typeof window!=='undefined'?window:globalThis,()=>{
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const CANON={width:1600,height:1000,energyPanel:{x:.700,y:.100,w:.295,h:.250},energyPlot:{x:.735,y:.135,w:.240,h:.160}};
function solve(A,b){const n=A.length,M=A.map((r,i)=>[...r,b[i]]);for(let c=0;c<n;c++){let p=c;for(let r=c+1;r<n;r++)if(Math.abs(M[r][c])>Math.abs(M[p][c]))p=r;if(Math.abs(M[p][c])<1e-10)return null;[M[c],M[p]]=[M[p],M[c]];const q=M[c][c];for(let j=c;j<=n;j++)M[c][j]/=q;for(let r=0;r<n;r++){if(r===c)continue;const f=M[r][c];for(let j=c;j<=n;j++)M[r][j]-=f*M[c][j];}}return M.map(r=>r[n]);}
function homographyFrom4(src,dst){const A=[],b=[];for(let i=0;i<4;i++){const x=src[i].x,y=src[i].y,u=dst[i].x,v=dst[i].y;A.push([x,y,1,0,0,0,-u*x,-u*y]);b.push(u);A.push([0,0,0,x,y,1,-v*x,-v*y]);b.push(v);}const h=solve(A,b);return h?[...h,1]:null;}
function inv3(m){const [a,b,c,d,e,f,g,h,i]=m,A=e*i-f*h,B=-(d*i-f*g),C=d*h-e*g,D=-(b*i-c*h),E=a*i-c*g,F=-(a*h-b*g),G=b*f-c*e,H=-(a*f-c*d),I=a*e-b*d,det=a*A+b*B+c*C;if(Math.abs(det)<1e-10)return null;return[A/det,D/det,G/det,B/det,E/det,H/det,C/det,F/det,I/det];}
function mapPt(H,p){const z=H[6]*p.x+H[7]*p.y+H[8];return{x:(H[0]*p.x+H[1]*p.y+H[2])/z,y:(H[3]*p.x+H[4]*p.y+H[5])/z};}
function detectWindowQuad(ctx,canvas){
 const W=canvas.width,H=canvas.height,d=ctx.getImageData(0,0,W,H).data,lum=(x,y)=>{x=Math.max(0,Math.min(W-1,x|0));y=Math.max(0,Math.min(H-1,y|0));const i=(y*W+x)*4;return(d[i]+d[i+1]+d[i+2])/3;};
 const rows=[],cols=[],ys=Math.max(3,Math.round(H/220)),xs=Math.max(3,Math.round(W/240));
 for(let y=Math.round(H*.03);y<H*.93;y+=ys){let pale=0,dark=0,n=0;for(let x=0;x<W;x+=xs){const L=lum(x,y);if(L>155)pale++;if(L<95)dark++;n++;}if(pale/n>.24&&(pale+dark)/n>.48)rows.push(y);}
 for(let x=Math.round(W*.02);x<W*.98;x+=xs){let pale=0,dark=0,n=0;for(let y=0;y<H;y+=ys){const L=lum(x,y);if(L>155)pale++;if(L<95)dark++;n++;}if(pale/n>.18&&(pale+dark)/n>.40)cols.push(x);}
 if(rows.length<8||cols.length<8)return{ok:false,reason:'window-structure-insufficient'};
 const top=Math.min(...rows),bottom=Math.max(...rows),left=Math.min(...cols),right=Math.max(...cols),ww=right-left,hh=bottom-top;
 if(ww<W*.45||hh<H*.35)return{ok:false,reason:'window-bounds-too-small'};
 const ep={x:left+ww*CANON.energyPanel.x,y:top+hh*CANON.energyPanel.y,w:ww*CANON.energyPanel.w,h:hh*CANON.energyPanel.h};
 let dark=0,green=0,n=0;for(let y=ep.y;y<ep.y+ep.h;y+=Math.max(2,ep.h/40)){for(let x=ep.x;x<ep.x+ep.w;x+=Math.max(2,ep.w/65)){const ix=Math.max(0,Math.min(W-1,x|0)),iy=Math.max(0,Math.min(H-1,y|0)),i=(iy*W+ix)*4,r=d[i],g=d[i+1],b=d[i+2],L=(r+g+b)/3;if(L<125)dark++;if(g>50&&g>r*1.05&&g>b*.9)green++;n++;}}
 const dr=dark/Math.max(1,n),gr=green/Math.max(1,n),conf=clamp(.45+dr*.25+gr*2.2,.35,.95);
 return{ok:conf>=.48,quad:[{x:left,y:top},{x:right,y:top},{x:right,y:bottom},{x:left,y:bottom}],confidence:conf,validation:{dark:dr,green:gr},source:'screen-structure-registration'};
}
function warpToCanonical(srcCanvas,quad){
 const out=document.createElement('canvas');out.width=CANON.width;out.height=CANON.height;const octx=out.getContext('2d',{willReadFrequently:true}),sctx=srcCanvas.getContext('2d',{willReadFrequently:true}),src=sctx.getImageData(0,0,srcCanvas.width,srcCanvas.height),dst=octx.createImageData(out.width,out.height),canon=[{x:0,y:0},{x:out.width-1,y:0},{x:out.width-1,y:out.height-1},{x:0,y:out.height-1}],H=homographyFrom4(quad,canon),I=H?inv3(H):null;if(!I)return null;
 for(let y=0;y<out.height;y++)for(let x=0;x<out.width;x++){const p=mapPt(I,{x,y}),sx=Math.round(p.x),sy=Math.round(p.y),di=(y*out.width+x)*4;if(sx>=0&&sy>=0&&sx<srcCanvas.width&&sy<srcCanvas.height){const si=(sy*srcCanvas.width+sx)*4;dst.data[di]=src.data[si];dst.data[di+1]=src.data[si+1];dst.data[di+2]=src.data[si+2];dst.data[di+3]=255;}else dst.data[di+3]=255;}
 octx.putImageData(dst,0,0);return{canvas:out,H,inv:I};
}
function rect(c,r){return{x:c.width*r.x,y:c.height*r.y,w:c.width*r.w,h:c.height*r.h};}
function register(ctx,canvas,manualQuad=null){const det=manualQuad?{ok:true,quad:manualQuad,confidence:1,source:'manual-4point'}:detectWindowQuad(ctx,canvas);if(!det?.ok)return{ok:false,reason:det?.reason||'registration-failed',detector:det};const w=warpToCanonical(canvas,det.quad);if(!w)return{ok:false,reason:'homography-failed',detector:det};return{ok:true,source:det.source,confidence:det.confidence,quad:det.quad,canonical:w.canvas,H:w.H,inv:w.inv,energyPanel:rect(w.canvas,CANON.energyPanel),energyPlot:rect(w.canvas,CANON.energyPlot),validation:det.validation||null};}
return{CANON,detectWindowQuad,homographyFrom4,warpToCanonical,register,mapPt};
});
