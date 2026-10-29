import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

export default function RiskDistribution({data}) {
  return <ResponsiveContainer width="100%" height={240}>
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 4" stroke="var(--hairline)" vertical={false}/>
      <XAxis dataKey="range" stroke="var(--text-quiet)" tickLine={false} axisLine={false} fontSize={12}/>
      <YAxis stroke="var(--text-quiet)" allowDecimals={false} tickLine={false} axisLine={false} width={28}/>
      <Tooltip cursor={{fill:'var(--surface-hover)'}} contentStyle={{background:'var(--surface)',border:'1px solid var(--hairline)',borderRadius:10,color:'var(--text-main)'}}/>
      <Bar dataKey="count" name="Transactions" fill="var(--bar)" radius={[3,3,0,0]} maxBarSize={40} isAnimationActive={false}/>
    </BarChart>
  </ResponsiveContainer>;
}
