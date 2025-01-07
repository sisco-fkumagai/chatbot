import React, { useState, useEffect } from 'react';
import axios from 'axios';
import MessageBubble from './MessageBubble';

const ChatBot = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isComposing, setIsComposing] = useState(false); // 変換中かどうかを追跡
    const [isMessageLoading, setIsMessageLoading] = useState(true); // 初期メッセージのローディング状態

    //'こんにちは！私は採用面接の日程調整をお手伝いするチャットボットです。面接を希望する日時を教えていただけますか？'
    // 初期化処理
    useEffect(() => {
        const initializeChatBot = async () => {
            try {
                // 初期メッセージのローディング中
                await new Promise((resolve) => setTimeout(resolve, 2000)); // ダミーの遅延

                // 初期メッセージの設定
                const initialMessage = {
                    role: 'bot',
                    content: "こんにちは！私は採用活動をお手伝いするチャットボットです。\n面接の日程調整や採用活動に関する質問ができます。どちらを希望しますか？",
                };
                setMessages([initialMessage]);
            } finally {
                setIsMessageLoading(false); // ローディング終了
            }
        };

        initializeChatBot();
    }, []);

    // ユーザーからのメッセージ送信処理
    const sendMessage = async () => {
        if (input.trim() === '') return;

        // ユーザーのメッセージを追加
        const userMessage = { role: 'user', content: input };
        setMessages([...messages, userMessage]);
        setInput('');// 入力欄をクリア

        try {
            // サーバーとの通信
            const response = await axios.post('${process.env.REACT_APP_BACKEND_URL}/chat', {
                message: input,
                context: messages.map(msg => ({
                    role: msg.role,
                    content: msg.content,
                })),
            });

            // サーバーの応答を追加
            const botMessage = { role: 'bot', content: response.data.reply };
            setMessages((prev) => [...prev, botMessage]);
        } catch (error) {
            console.error('エラー:', error.response?.data || error.message);
            setMessages((prev) => [
                ...prev,
                { role: 'bot', content: '申し訳ありませんが、エラーが発生しました。' },
            ]);
        }
    };

    // Enterキーでメッセージ送信
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !isComposing) {
            e.preventDefault(); // デフォルトのEnter動作を防ぐ
            sendMessage(); //送信処理を実行
        }
    };

    return (
        <div className="chatbot">
            <div className="messages">
                {isMessageLoading ? (
                    <MessageBubble role="bot" isLoading={true} />
                ) : (
                    // 初期メッセージまたは通常のメッセージ表示
                    messages.map((msg, index) => (
                        <MessageBubble key={index} role={msg.role} content={msg.content} />
                    ))
                )}
            </div>
            <div className="input-container">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown} // Enterキーの押下処理
                    onCompositionStart={() => setIsComposing(true)} // IME変換開始
                    onCompositionEnd={() => setIsComposing(false)} // IME変換終了
                    placeholder="メッセージを入力..."
                />
                <button onClick={sendMessage}>送信</button>
            </div>
        </div>
    );
};

export default ChatBot;
