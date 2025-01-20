import React, { useState, useEffect } from 'react';
import axios from 'axios';
import MessageBubble from './MessageBubble';
import { v4 as uuidv4 } from 'uuid'; // ユニークID生成用

const ChatBot = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isComposing, setIsComposing] = useState(false); // 変換中かどうかを追跡
    const [isLoading, setIsLoading] = useState(false); // メッセージ送信中の状態
    const [isInitialLoading, setIsInitialLoading] = useState(true); // 初期メッセージのローディング状態
    const [userId, setUserId] = useState(localStorage.getItem('user_id') || uuidv4()); // ユーザーIDを保持

    // 環境変数からバックエンドAPI URLを取得
    const apiUrl = process.env.REACT_APP_BACKEND_API_URL;

    useEffect(() => {
        // ユーザーIDをローカルストレージに保存
        localStorage.setItem('user_id', userId);
    }, [userId]);

    // 初期化処理
    useEffect(() => {
        const initializeChatBot = async () => {
            try {
                // 初期メッセージのローディング中
                await new Promise((resolve) => setTimeout(resolve, 1000)); // ダミーの遅延

                // 初期メッセージを設定
                const initialMessage = {
                    role: 'bot',
                    content: "こんにちは！私は採用活動をお手伝いするチャットボットです。\n以下のことができます。 \n 1. 面接の日程調整 \n 2. 採用活動に関する質問 \nどちらを希望しますか？ (番号で返答ください。)"
                };
                setMessages([initialMessage]);
            } finally {
                setIsInitialLoading(false); // 初期ローディング終了
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

        setIsLoading(true);

        try {
            // サーバーとの通信
            const response = await axios.post(`${apiUrl}/chat`, {
                message: input,
                context: messages.map(msg => ({
                    role: msg.role,
                    content: msg.content,
                })),
                user_id: userId, // ユーザーIDを送信
            });
            const chatResponse = response.data.reply;

            // デバッグログを表示
            if (response.data.debug_log) {
                console.group("デバッグログ");
                response.data.debug_log.forEach((log) => console.log(log));
                console.groupEnd();
            }

            // 日程調整の応答
            if (chatResponse.includes("候補日程")) {
                const options = chatResponse.split("\n").slice(1); // 候補日程を抽出
                setMessages((prev) => [
                    ...prev,
                    { role: "bot", content: "次の候補日程はいかがでしょうか？" },
                    ...options.map(option => ({ role: "bot", content: option })),
                ]);
            }
            // FAQ応答
            else if (chatResponse.includes("FAQ")) {
                setMessages((prev) => [
                    ...prev,
                    { role: "bot", content: chatResponse }
                ]);
            }
            // その他の応答
            else {
                // サーバーの応答を追加
                setMessages((prev) => [
                    ...prev,
                    { role: 'bot', content: chatResponse }
                ]);
            }
        } catch (error) {
            console.error('エラー:', error.response?.data || error.message);
            setMessages((prev) => [
                ...prev,
                { role: 'bot', content: '申し訳ありませんが、エラーが発生しました。' },
            ]);
        } finally {
            setIsLoading(false);
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
                {isInitialLoading ? (
                    <MessageBubble role="bot" isLoading={true} />
                ) : (
                    messages.map((msg, index) => (
                        <MessageBubble key={index} role={msg.role} content={msg.content} />
                    ))
                )}
                {isLoading && <MessageBubble role="bot" isLoading={true} />}
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
