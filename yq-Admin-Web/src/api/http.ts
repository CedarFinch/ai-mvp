import axios from 'axios';
import { message } from 'antd';

interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

const http = axios.create({
  baseURL: '/yq-admin',
  timeout: 15000,
});

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface StreamHandlers {
  onEvent: (event: StreamEvent) => void;
  onError?: (error: Error) => void;
}

let redirectingToLogin = false;

const clearAuthAndRedirect = () => {
  localStorage.removeItem('yanque_token');
  localStorage.removeItem('yanque_sign_secret');
  localStorage.removeItem('yanque_user');
  localStorage.removeItem('yanque_roles');
  localStorage.removeItem('yanque_permissions');
  if (redirectingToLogin || window.location.pathname === '/login') {
    return;
  }
  redirectingToLogin = true;
  message.warning('登录状态已失效，请重新登录');
  window.setTimeout(() => {
    window.location.href = '/login';
  }, 1200);
};

const handleUnauthorized = (code?: number, text?: string) => {
  if (code === 401) {
    clearAuthAndRedirect();
    return;
  }
  if (code === 403) {
    message.error(text || '暂无权限访问该接口');
    return;
  }
  message.error(text || '请求失败');
};

const createNonce = () => {
  const bytes = new Uint8Array(16);
  window.crypto.getRandomValues(bytes);
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
};

const appendParams = (searchParams: URLSearchParams, params: unknown) => {
  if (!params || typeof params !== 'object') {
    return;
  }
  Object.entries(params as Record<string, unknown>).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((item) => searchParams.append(key, String(item)));
      return;
    }
    searchParams.append(key, String(value));
  });
};

const sanitizeParams = (params: unknown) => {
  if (!params || typeof params !== 'object') {
    return params;
  }
  return Object.entries(params as Record<string, unknown>).reduce<Record<string, unknown>>((result, [key, value]) => {
    if (value === undefined || value === null || value === '') {
      return result;
    }
    if (Array.isArray(value)) {
      const items = value.filter((item) => item !== undefined && item !== null && item !== '');
      if (items.length > 0) {
        result[key] = items;
      }
      return result;
    }
    result[key] = value;
    return result;
  }, {});
};

const buildSignTarget = (baseURL: string | undefined, requestUrl: string | undefined, params: unknown) => {
  const url = new URL(`${baseURL || ''}${requestUrl || ''}`, window.location.origin);
  appendParams(url.searchParams, params);
  return {
    uri: url.pathname,
    query: url.searchParams.toString(),
  };
};

const hmacSha256Hex = async (source: string, secret: string) => {
  const encoder = new TextEncoder();
  const key = await window.crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const signature = await window.crypto.subtle.sign('HMAC', key, encoder.encode(source));
  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, '0')).join('');
};

http.interceptors.request.use(async (config) => {
  const token = localStorage.getItem('yanque_token');
  const signSecret = localStorage.getItem('yanque_sign_secret');
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  if (token && signSecret) {
    config.params = sanitizeParams(config.params);
    const timestamp = String(Date.now());
    const nonce = createNonce();
    const method = (config.method || 'GET').toUpperCase();
    const target = buildSignTarget(config.baseURL, config.url, config.params);
    const source = `${method}\n${target.uri}\n${target.query}\n${timestamp}\n${nonce}`;
    const sign = await hmacSha256Hex(source, signSecret);
    config.headers.set('X-Timestamp', timestamp);
    config.headers.set('X-Nonce', nonce);
    config.headers.set('X-Sign', sign);
  }
  return config;
});

http.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse<unknown>;
    if (body && typeof body.code === 'number' && body.code !== 200) {
      handleUnauthorized(body.code, body.message);
      return Promise.reject(new Error(body.message || '请求失败'));
    }
    return body?.data ?? response.data;
  },
  (error) => {
    const code = error?.response?.data?.code || error?.response?.status;
    handleUnauthorized(code, error?.response?.data?.message || error.message || '网络异常');
    return Promise.reject(error);
  },
);

const parseStreamBlock = (block: string): StreamEvent | undefined => {
  let event = '';
  const dataLines: string[] = [];
  block.split(/\r?\n/).forEach((line) => {
    if (line.startsWith('event:')) {
      event = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trimStart());
    }
  });
  const data = dataLines.join('\n');
  if (!event || !data) {
    return undefined;
  }
  return { event, data: JSON.parse(data) as Record<string, unknown> };
};

const readEventStream = async (response: Response, handlers: StreamHandlers) => {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('浏览器不支持流式响应');
  }
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() || '';
    blocks.forEach((block) => {
      const event = parseStreamBlock(block);
      if (event) {
        handlers.onEvent(event);
      }
    });
  }
  const event = parseStreamBlock(buffer);
  if (event) {
    handlers.onEvent(event);
  }
};

export const streamPost = async (
  url: string,
  data: unknown,
  handlers: StreamHandlers,
  signal?: AbortSignal,
) => {
  const token = localStorage.getItem('yanque_token');
  const signSecret = localStorage.getItem('yanque_sign_secret');
  const timestamp = String(Date.now());
  const nonce = createNonce();
  const requestUrl = `/yq-admin${url}`;
  const headers = new Headers({
    Accept: 'text/event-stream',
    'Content-Type': 'application/json; charset=UTF-8',
  });

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (token && signSecret) {
    const source = `POST\n${requestUrl}\n\n${timestamp}\n${nonce}`;
    headers.set('X-Timestamp', timestamp);
    headers.set('X-Nonce', nonce);
    headers.set('X-Sign', await hmacSha256Hex(source, signSecret));
  }

  try {
    const response = await fetch(requestUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
      signal,
    });
    if (!response.ok) {
      const text = await response.text();
      handleUnauthorized(response.status, text || '请求失败');
      throw new Error(text || '请求失败');
    }
    await readEventStream(response, handlers);
  } catch (error) {
    if ((error as Error).name === 'AbortError') {
      return;
    }
    handlers.onError?.(error as Error);
    throw error;
  }
};

export default http;
