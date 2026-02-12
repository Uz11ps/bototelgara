
export const WebApp = (window as any).Telegram?.WebApp || {
    ready: () => { },
    expand: () => { },
    sendData: (data: string) => console.log('SendData:', data),
    close: () => { console.log('WebApp.close()') },
};
