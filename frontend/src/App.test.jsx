import React from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import App from './App';
import { predict, request } from './api';
vi.mock('./api', () => ({request:vi.fn(),predict:vi.fn(),predictCSV:vi.fn()}));
beforeEach(()=>{localStorage.clear();request.mockRejectedValue(new Error('API offline'));predict.mockReset();});
afterEach(()=>cleanup());
it('submits all eight typed signals and renders the returned score', async()=>{
  predict.mockResolvedValue({data:{result:{prediction:'legitimate',risk_score:.123,model_version:'test-artifact',dataset_kind:'synthetic',message:'Below threshold',indicators:[]},timings:{preprocessing_ms:1,inference_ms:2,pipeline_ms:3}},timing:{serverMs:5,roundTripMs:7,overheadMs:2}});
  render(<App/>);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button',{name:'Analyze transaction'}));
  fireEvent.click(within(screen.getByRole('main')).getByRole('button',{name:'Analyze transaction',exact:true}));
  expect(await screen.findByText('12.3%')).toBeInTheDocument();
  expect(predict).toHaveBeenCalledWith({amount:149.5,hour:14,transactions_24h:3,distance_km:12,account_age_days:730,international:false,new_device:false,merchant_category:'retail'});
  expect(screen.getByText('test-artifact')).toBeInTheDocument();
});
it('shows prediction errors and re-enables submit', async()=>{
  predict.mockRejectedValue(new Error('Model unavailable'));
  render(<App/>);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button',{name:'Analyze transaction'}));
  fireEvent.click(within(screen.getByRole('main')).getByRole('button',{name:'Analyze transaction',exact:true}));
  expect(await screen.findByText('Model unavailable',{selector:'.notice.error'})).toBeInTheDocument();
  expect(within(screen.getByRole('main')).getByRole('button',{name:'Analyze transaction',exact:true})).toBeEnabled();
});

it.each(['amount','category','device'])('clears a previous assessment after editing %s without submitting again', async field=>{
  predict.mockResolvedValue({data:{result:{prediction:'legitimate',risk_score:.123,model_version:'test-artifact',dataset_kind:'synthetic',message:'Below threshold',indicators:[]},timings:{preprocessing_ms:1,inference_ms:2,pipeline_ms:3}},timing:{serverMs:5,roundTripMs:7,overheadMs:2}});
  render(<App/>);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button',{name:'Analyze transaction'}));
  fireEvent.click(within(screen.getByRole('main')).getByRole('button',{name:'Analyze transaction',exact:true}));
  expect(await screen.findByText('12.3%')).toBeInTheDocument();
  if (field==='amount') fireEvent.change(screen.getByLabelText(/Transaction amount/),{target:{value:'-1'}});
  if (field==='category') fireEvent.change(screen.getByLabelText(/Merchant category/),{target:{value:'travel'}});
  if (field==='device') fireEvent.click(screen.getByLabelText('New device'));
  expect(screen.queryByText('12.3%')).not.toBeInTheDocument();
  expect(screen.getByText('Ready when you are')).toBeInTheDocument();
  expect(predict).toHaveBeenCalledTimes(1);
});

it('prevents edits while the current transaction is being analyzed', async()=>{
  let finish;
  predict.mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  render(<App/>);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button',{name:'Analyze transaction'}));
  fireEvent.click(within(screen.getByRole('main')).getByRole('button',{name:'Analyze transaction',exact:true}));
  expect(screen.getByLabelText(/Transaction amount/)).toBeDisabled();
  expect(screen.getByLabelText(/Merchant category/)).toBeDisabled();
  expect(screen.getByLabelText('New device')).toBeDisabled();
  await act(async()=>finish({data:{result:{prediction:'legitimate',risk_score:.123,model_version:'test-artifact',dataset_kind:'synthetic',message:'Below threshold',indicators:[]},timings:{preprocessing_ms:1,inference_ms:2,pipeline_ms:3}},timing:{serverMs:5,roundTripMs:7,overheadMs:2}}));
  expect(await screen.findByText('12.3%')).toBeInTheDocument();
  expect(screen.getByLabelText(/Transaction amount/)).toBeEnabled();
});

it('switches between dark and light and saves the selection',()=>{
  render(<App/>);
  expect(document.documentElement).toHaveClass('dark');
  fireEvent.click(screen.getByRole('button',{name:'Toggle theme'}));
  expect(document.documentElement).not.toHaveClass('dark');
  expect(localStorage.getItem('chaiui-theme')).toBe('light');
  fireEvent.click(screen.getByRole('button',{name:'Toggle theme'}));
  expect(document.documentElement).toHaveClass('dark');
});

it('restores a saved light theme on the first render',()=>{
  localStorage.setItem('chaiui-theme','light');
  render(<App/>);
  expect(document.documentElement).not.toHaveClass('dark');
});

it('preserves typed input and avoids extra health requests across animated page changes',()=>{
  render(<App/>);
  const nav=within(screen.getByRole('navigation'));
  fireEvent.click(nav.getByRole('button',{name:'Analyze transaction'}));
  fireEvent.change(screen.getByLabelText(/Transaction amount/),{target:{value:'321.50'}});
  const healthCalls=request.mock.calls.length;
  fireEvent.click(nav.getByRole('button',{name:'Help center'}));
  fireEvent.click(nav.getByRole('button',{name:'Analyze transaction'}));
  expect(screen.getByLabelText(/Transaction amount/)).toHaveValue(321.5);
  expect(request).toHaveBeenCalledTimes(healthCalls);
  expect(predict).not.toHaveBeenCalled();
});

it('keeps session history until the user confirms clearing it',async()=>{
  predict.mockResolvedValue({data:{result:{prediction:'legitimate',risk_score:.123,model_version:'test-artifact',dataset_kind:'synthetic',message:'Below threshold',indicators:[]},timings:{preprocessing_ms:1,inference_ms:2,pipeline_ms:3}},timing:{serverMs:5,roundTripMs:7,overheadMs:2}});
  render(<App/>);
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button',{name:'Analyze transaction'}));
  fireEvent.click(within(screen.getByRole('main')).getByRole('button',{name:'Analyze transaction',exact:true}));
  await screen.findByText('12.3%');
  fireEvent.click(within(screen.getByRole('navigation')).getByRole('button',{name:/Transaction history/}));
  const clear=within(screen.getByRole('main')).getByRole('button',{name:'Clear history'});
  fireEvent.click(clear);
  const keep=within(screen.getByRole('alertdialog')).getByRole('button',{name:'Keep history'});
  await waitFor(()=>expect(keep).toHaveFocus());
  fireEvent.click(keep);
  expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  expect(screen.getByText('12.3%')).toBeInTheDocument();
  fireEvent.click(clear);
  fireEvent.click(within(screen.getByRole('alertdialog')).getByRole('button',{name:'Clear history'}));
  expect(screen.getByText('No matching transactions')).toBeInTheDocument();
  expect(clear).toBeDisabled();
});
