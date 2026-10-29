import React from 'react';
import {afterEach, beforeEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen} from '@testing-library/react';
import ChatWidget from './ChatWidget';
import {request} from './api';
vi.mock('./api',()=>({request:vi.fn()}));
beforeEach(()=>{request.mockReset();});
afterEach(cleanup);
function open() {render(<ChatWidget/>); fireEvent.click(screen.getByRole('button',{name:'Open SafePay assistant'}));}
it('opens, focuses the question and restores focus on Escape',()=>{
  open(); expect(screen.getByLabelText('Your question')).toHaveFocus();
  fireEvent.keyDown(screen.getByLabelText('Your question'),{key:'Escape'});
  expect(screen.getByRole('button',{name:'Open SafePay assistant'})).toHaveFocus();
});
it('sends only the question and displays plain text',async()=>{
  request.mockResolvedValue({data:{answer:'Synthetic data only.'}}); open();
  fireEvent.change(screen.getByLabelText('Your question'),{target:{value:'Which dataset?'}});
  fireEvent.click(screen.getByRole('button',{name:'Send'}));
  expect(await screen.findByText('Synthetic data only.')).toBeInTheDocument();
  expect(JSON.parse(request.mock.calls[0][1].body)).toEqual({message:'Which dataset?'});
});
it('shows API errors and preserves the question for retry',async()=>{
  request.mockRejectedValue(new Error('Chat is not configured.')); open();
  fireEvent.change(screen.getByLabelText('Your question'),{target:{value:'Explain fraud'}});
  fireEvent.click(screen.getByRole('button',{name:'Send'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Chat is not configured.');
  expect(screen.getByLabelText('Your question')).toHaveValue('Explain fraud');
  expect(screen.getByRole('button',{name:'Send'})).toBeEnabled();
});
