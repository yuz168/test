const supabaseUrl = 'https://xtwddjnwjtjmwrxckjhe.supabase.co'; // ここにあなたのSupabaseプロジェクトURLを入力
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0d2Rkam53anRqbXdyeGNramhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NzU0ODI0OSwiZXhwIjoyMDYzMTI0MjQ5fQ.-EOnF6GOZogKBzOErRREEfnsWGG-o1IlmxdbRGQH0b8'; // ここにあなたのSupabase匿名キーを入力
const supabase = createClient(supabaseUrl, supabaseAnonKey);

const postForm = document.getElementById('post-form');
const postList = document.getElementById('posts');
const submitButton = document.getElementById('submit-button');

async function loadPosts() {
    const { data, error } = await supabase
        .from('posts')
        .select('*')
        .order('created_at', { ascending: false });

    if (error) {
        console.error('投稿の読み込みエラー:', error);
        return;
    }

    postList.innerHTML = '';
    data.forEach(post => {
        const listItem = document.createElement('li');
        listItem.innerHTML = `
            <div class="post-info">
                名前：${post.name} (投稿日時：${new Date(post.created_at).toLocaleString()})
            </div>
            <p>${post.content}</p>
        `;
        postList.appendChild(listItem);
    });
}

submitButton.addEventListener('click', async (event) => {
    event.preventDefault();

    const nameInput = document.getElementById('name');
    const passwordInput = document.getElementById('password');
    const contentInput = document.getElementById('content');

    const name = nameInput.value.trim();
    const password = passwordInput.value;
    const content = contentInput.value.trim();

    if (!name || !content) {
        alert('名前と投稿内容は必須です。');
        return;
    }

    const passwordHash = crc32(password).toString(16); // パスワードをCRC32でハッシュ化

    const { error } = await supabase
        .from('posts')
        .insert([{ name, content, password_hash }]);

    if (error) {
        console.error('投稿エラー:', error);
        alert('投稿に失敗しました。');
    } else {
        nameInput.value = '';
        passwordInput.value = '';
        contentInput.value = '';
        loadPosts(); // 投稿後に一覧を再読み込み
    }
});

// ページのロード時に投稿を読み込む
loadPosts();
