import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function RiskDistribution({data}) {
  return <ResponsiveContainer width="100%" height={240}>
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 4" stroke="#243044" vertical={false}/>
      <XAxis dataKey="range" stroke="#a3b1c8" tickLine={false} axisLine={false} fontSize={12}/>
      <YAxis stroke="#a3b1c8" allowDecimals={false} tickLine={false} axisLine={false} width={28}/>
      <Tooltip cursor={{fill:'#17243a'}} contentStyle={{background:'#121d2f',border:'1px solid #30415b',borderRadius:10,color:'#e7edf8'}}/>
      <Bar dataKey="count" name="Transactions" fill="#36cfbb" radius={[5,5,0,0]} maxBarSize={48} isAnimationActive={false}/>
    </BarChart>
  </ResponsiveContainer>;
}
