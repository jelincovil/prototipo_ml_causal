#include <windows.h>
#include <bcrypt.h>
#include <commctrl.h>
#include <shellapi.h>
#include <shlobj.h>
#include <winhttp.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cwchar>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iterator>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <vector>

namespace {

namespace fs = std::filesystem;
using namespace std::chrono_literals;

constexpr wchar_t kWindowClass[] = L"PuenteCausalVentana";
constexpr wchar_t kProjectUrl[] =
    L"https://codeload.github.com/jelincovil/prototipo_ml_causal/zip/refs/tags/v1.0.1";
constexpr wchar_t kUvVersion[] = L"0.13.8";
constexpr wchar_t kUvX64Url[] =
    L"https://github.com/astral-sh/uv/releases/download/0.13.8/"
    L"uv-x86_64-pc-windows-msvc.zip";
constexpr wchar_t kUvArm64Url[] =
    L"https://github.com/astral-sh/uv/releases/download/0.13.8/"
    L"uv-aarch64-pc-windows-msvc.zip";
constexpr wchar_t kUvX64Sha256[] =
    L"529e78a9cec6cd7e3e014f7ecd8bda0c113969d4ed0f2efeedb85c30943325b8";
constexpr wchar_t kUvArm64Sha256[] =
    L"59e6d919bed1f72035e622a7c930058f08a8931c4c78ceaf9f56e7fb74dd2c48";
constexpr wchar_t kBaseUrl[] = L"http://127.0.0.1:8000";
constexpr wchar_t kChampion[] = L"v0008";
constexpr UINT kMessageLog = WM_APP + 1;
constexpr UINT kMessageDone = WM_APP + 2;
constexpr int kInstall = 1001;
constexpr int kStart = 1002;
constexpr int kStop = 1003;
constexpr int kOpenEffect = 1004;
constexpr int kOpenDocs = 1005;
constexpr int kOpenLog = 1006;
constexpr int kRepair = 1007;

struct Handle {
    HANDLE value = nullptr;
    ~Handle() {
        if (value && value != INVALID_HANDLE_VALUE) {
            CloseHandle(value);
        }
    }
    Handle() = default;
    explicit Handle(HANDLE handle) : value(handle) {}
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
    HANDLE release() {
        HANDLE result = value;
        value = nullptr;
        return result;
    }
    void reset(HANDLE handle = nullptr) {
        if (value && value != INVALID_HANDLE_VALUE) {
            CloseHandle(value);
        }
        value = handle;
    }
};

struct InternetHandle {
    HINTERNET value = nullptr;
    ~InternetHandle() {
        if (value) {
            WinHttpCloseHandle(value);
        }
    }
    InternetHandle() = default;
    explicit InternetHandle(HINTERNET handle) : value(handle) {}
};

struct BcryptAlgorithm {
    BCRYPT_ALG_HANDLE value = nullptr;
    ~BcryptAlgorithm() {
        if (value) {
            BCryptCloseAlgorithmProvider(value, 0);
        }
    }
};

struct BcryptHash {
    BCRYPT_HASH_HANDLE value = nullptr;
    ~BcryptHash() {
        if (value) {
            BCryptDestroyHash(value);
        }
    }
};

struct ServiceProcess {
    HANDLE process = nullptr;
    HANDLE job = nullptr;
    DWORD pid = 0;
};

enum class Operation { refresh, install, repair, start, stop };

struct Completion {
    Operation operation = Operation::refresh;
    bool ok = false;
    bool running = false;
    std::wstring message;
};

struct Health {
    bool ours = false;
    bool integrity = false;
    std::string version;
    std::string gate;
};

HWND g_window = nullptr;
HWND g_status = nullptr;
HWND g_path = nullptr;
HWND g_log_view = nullptr;
HWND g_progress = nullptr;
HWND g_install_button = nullptr;
HWND g_start_button = nullptr;
HWND g_stop_button = nullptr;
HWND g_repair_button = nullptr;
HFONT g_text_font = nullptr;
HFONT g_title_font = nullptr;
HFONT g_mono_font = nullptr;
std::thread g_worker;
std::mutex g_log_mutex;
std::mutex g_service_mutex;
std::ofstream g_log_file;
ServiceProcess g_service;
bool g_busy = false;

std::wstring Utf8ToWide(std::string_view input) {
    if (input.empty()) {
        return {};
    }
    UINT code_page = CP_UTF8;
    DWORD flags = MB_ERR_INVALID_CHARS;
    int length = MultiByteToWideChar(code_page, flags, input.data(),
                                     static_cast<int>(input.size()), nullptr, 0);
    if (length == 0) {
        code_page = CP_ACP;
        flags = 0;
        length = MultiByteToWideChar(code_page, flags, input.data(),
                                     static_cast<int>(input.size()), nullptr, 0);
    }
    if (length == 0) {
        return L"[texto no decodificable]";
    }
    std::wstring result(static_cast<size_t>(length), L'\0');
    MultiByteToWideChar(code_page, flags, input.data(), static_cast<int>(input.size()),
                        result.data(), length);
    return result;
}

std::string WideToUtf8(std::wstring_view input) {
    if (input.empty()) {
        return {};
    }
    int length = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, input.data(),
                                     static_cast<int>(input.size()), nullptr, 0, nullptr, nullptr);
    if (length == 0) {
        throw std::runtime_error("No se pudo codificar un mensaje en UTF-8.");
    }
    std::string result(static_cast<size_t>(length), '\0');
    WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, input.data(),
                        static_cast<int>(input.size()), result.data(), length, nullptr, nullptr);
    return result;
}

std::wstring WindowsError(DWORD code, std::wstring_view action) {
    wchar_t* raw = nullptr;
    DWORD count = FormatMessageW(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM |
            FORMAT_MESSAGE_IGNORE_INSERTS,
        nullptr, code, 0, reinterpret_cast<wchar_t*>(&raw), 0, nullptr);
    std::wstring detail = count && raw ? std::wstring(raw, count)
                                       : L"error de Windows " + std::to_wstring(code);
    if (raw) {
        LocalFree(raw);
    }
    while (!detail.empty() && (detail.back() == L'\r' || detail.back() == L'\n')) {
        detail.pop_back();
    }
    return std::wstring(action) + L". Código " + std::to_wstring(code) + L": " + detail;
}

std::wstring Timestamp() {
    SYSTEMTIME now{};
    GetLocalTime(&now);
    wchar_t text[32]{};
    swprintf_s(text, L"%02u:%02u:%02u", now.wHour, now.wMinute, now.wSecond);
    return text;
}

void AppendLog(const std::wstring& message) {
    std::wstring line = L"[" + Timestamp() + L"] " + message;
    {
        std::lock_guard lock(g_log_mutex);
        if (g_log_file.is_open()) {
            g_log_file << WideToUtf8(line) << "\n";
            g_log_file.flush();
        }
    }
    if (g_window) {
        PostMessageW(g_window, kMessageLog, 0,
                     reinterpret_cast<LPARAM>(new std::wstring(line)));
    }
}

fs::path InstallRoot() {
    PWSTR value = nullptr;
    HRESULT result = SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT,
                                          nullptr, &value);
    if (FAILED(result) || !value) {
        throw std::runtime_error(WideToUtf8(
            L"Windows no proporcionó la carpeta LocalAppData. Revisa el perfil de usuario."));
    }
    fs::path base(value);
    CoTaskMemFree(value);
    return base / L"PuenteCausal";
}

fs::path AppRoot() { return InstallRoot() / L"app"; }
fs::path VenvPython() { return AppRoot() / L".venv" / L"Scripts" / L"python.exe"; }
fs::path UvExecutable() { return InstallRoot() / L"herramientas" / L"uv" / L"uv.exe"; }
fs::path LogPath() { return InstallRoot() / L"registros" / L"lanzador.log"; }
fs::path ServiceLogPath() { return InstallRoot() / L"registros" / L"servicio.log"; }

void EnsureDirectory(const fs::path& directory) {
    std::error_code error;
    fs::create_directories(directory, error);
    if (error || !fs::is_directory(directory)) {
        throw std::runtime_error(WideToUtf8(
            L"No se pudo crear " + directory.wstring() + L". " +
            (error ? Utf8ToWide(error.message()) : L"La ruta no es una carpeta") +
            L". Revisa permisos, antivirus o Control de acceso a carpetas."));
    }
}

void CheckWriteAccess() {
    fs::path root = InstallRoot();
    fs::path parent = root.parent_path();
    if (!fs::is_directory(parent)) {
        throw std::runtime_error(WideToUtf8(L"No existe la carpeta base " + parent.wstring()));
    }
    if (!CreateDirectoryW(root.c_str(), nullptr)) {
        DWORD code = GetLastError();
        if (code != ERROR_ALREADY_EXISTS) {
            throw std::runtime_error(WideToUtf8(WindowsError(code, L"No se pudo crear " + root.wstring())));
        }
    }
    if (!fs::is_directory(root)) {
        throw std::runtime_error(WideToUtf8(root.wstring() + L" existe, pero no es una carpeta."));
    }
    EnsureDirectory(root / L"registros");
    fs::path test = root / L"registros" / L"prueba_escritura.tmp";
    Handle file(CreateFileW(test.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                            FILE_ATTRIBUTE_NORMAL, nullptr));
    if (file.value == INVALID_HANDLE_VALUE) {
        throw std::runtime_error(WideToUtf8(WindowsError(
            GetLastError(), L"No se pudo escribir en la carpeta de instalación")));
    }
    const char marker[] = "PuenteCausal\n";
    DWORD written = 0;
    if (!WriteFile(file.value, marker, static_cast<DWORD>(sizeof(marker) - 1), &written, nullptr) ||
        written != sizeof(marker) - 1) {
        throw std::runtime_error(WideToUtf8(WindowsError(
            GetLastError(), L"La prueba de escritura no se completó")));
    }
    file.reset();
    if (!DeleteFileW(test.c_str())) {
        throw std::runtime_error(WideToUtf8(WindowsError(
            GetLastError(), L"No se pudo retirar la prueba de escritura")));
    }
    AppendLog(L"Escritura comprobada en " + root.wstring());
}

std::wstring QuoteArgument(std::wstring_view value) {
    if (!value.empty() && value.find_first_of(L" \t\n\v\"") == std::wstring_view::npos) {
        return std::wstring(value);
    }
    std::wstring result = L"\"";
    size_t backslashes = 0;
    for (wchar_t character : value) {
        if (character == L'\\') {
            ++backslashes;
        } else if (character == L'\"') {
            result.append(backslashes * 2 + 1, L'\\');
            result.push_back(L'\"');
            backslashes = 0;
        } else {
            result.append(backslashes, L'\\');
            backslashes = 0;
            result.push_back(character);
        }
    }
    result.append(backslashes * 2, L'\\');
    result.push_back(L'\"');
    return result;
}

std::wstring CommandLine(const std::vector<std::wstring>& arguments) {
    std::wstring result;
    for (size_t index = 0; index < arguments.size(); ++index) {
        if (index) {
            result.push_back(L' ');
        }
        result += QuoteArgument(arguments[index]);
    }
    return result;
}

void CheckEnvironment(const wchar_t* name, const std::wstring& value) {
    if (!SetEnvironmentVariableW(name, value.c_str())) {
        throw std::runtime_error(WideToUtf8(WindowsError(
            GetLastError(), L"No se pudo configurar el entorno del proceso hijo")));
    }
}

void ConfigureToolEnvironment() {
    fs::path root = InstallRoot();
    CheckEnvironment(L"UV_CACHE_DIR", (root / L"cache").wstring());
    CheckEnvironment(L"UV_PYTHON_INSTALL_DIR", (root / L"herramientas" / L"python").wstring());
    CheckEnvironment(L"UV_NO_MODIFY_PATH", L"1");
    CheckEnvironment(L"PYTHONUTF8", L"1");
    CheckEnvironment(L"PYTHONUNBUFFERED", L"1");
}

struct ProcessResult {
    DWORD exit_code = 0;
};

ProcessResult RunProcess(const std::vector<std::wstring>& arguments,
                         const fs::path& working_directory) {
    std::wstring command = CommandLine(arguments);
    AppendLog(L"Ejecutando: " + command);
    SECURITY_ATTRIBUTES security{sizeof(security), nullptr, TRUE};
    Handle read_pipe;
    Handle write_pipe;
    if (!CreatePipe(&read_pipe.value, &write_pipe.value, &security, 0)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo capturar la salida")));
    }
    if (!SetHandleInformation(read_pipe.value, HANDLE_FLAG_INHERIT, 0)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo aislar la canalización")));
    }
    STARTUPINFOW startup{sizeof(startup)};
    startup.dwFlags = STARTF_USESHOWWINDOW | STARTF_USESTDHANDLES;
    startup.wShowWindow = SW_HIDE;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    startup.hStdOutput = write_pipe.value;
    startup.hStdError = write_pipe.value;
    PROCESS_INFORMATION information{};
    std::vector<wchar_t> buffer(command.begin(), command.end());
    buffer.push_back(L'\0');
    BOOL created = CreateProcessW(arguments.front().c_str(), buffer.data(), nullptr, nullptr, TRUE,
                                  CREATE_NO_WINDOW, nullptr, working_directory.c_str(),
                                  &startup, &information);
    if (!created) {
        throw std::runtime_error(WideToUtf8(WindowsError(
            GetLastError(), L"No se pudo iniciar " + arguments.front())));
    }
    Handle process(information.hProcess);
    Handle thread(information.hThread);
    write_pipe.reset();
    const auto deadline = std::chrono::steady_clock::now() + 20min;
    std::string output;
    for (;;) {
        DWORD available = 0;
        if (PeekNamedPipe(read_pipe.value, nullptr, 0, nullptr, &available, nullptr) && available) {
            char chunk[8192];
            DWORD amount = static_cast<DWORD>(
                std::min<size_t>(available, sizeof(chunk)));
            DWORD read = 0;
            if (ReadFile(read_pipe.value, chunk, amount, &read, nullptr) && read) {
                output.append(chunk, read);
                AppendLog(Utf8ToWide(std::string_view(chunk, read)));
            }
        }
        DWORD wait = WaitForSingleObject(process.value, 100);
        if (wait == WAIT_FAILED) {
            TerminateProcess(process.value, 1);
            throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"Falló la espera del proceso")));
        }
        if (wait == WAIT_OBJECT_0) {
            for (;;) {
                available = 0;
                if (!PeekNamedPipe(read_pipe.value, nullptr, 0, nullptr, &available, nullptr) ||
                    !available) {
                    break;
                }
                char chunk[8192];
                DWORD read = 0;
                DWORD amount = static_cast<DWORD>(std::min<size_t>(available, sizeof(chunk)));
                if (!ReadFile(read_pipe.value, chunk, amount, &read, nullptr) || !read) {
                    break;
                }
                output.append(chunk, read);
                AppendLog(Utf8ToWide(std::string_view(chunk, read)));
            }
            break;
        }
        if (std::chrono::steady_clock::now() > deadline) {
            TerminateProcess(process.value, 1);
            throw std::runtime_error(WideToUtf8(
                L"La operación superó 20 minutos y fue detenida. Revisa la red y el registro."));
        }
    }
    DWORD exit_code = 0;
    if (!GetExitCodeProcess(process.value, &exit_code)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se obtuvo el resultado del proceso")));
    }
    if (exit_code != 0) {
        throw std::runtime_error(WideToUtf8(
            L"El comando terminó con código " + std::to_wstring(exit_code) +
            L". La salida anterior contiene el motivo; no se declaró instalado el servicio."));
    }
    return {exit_code};
}

struct HttpResult {
    DWORD status = 0;
    std::string body;
};

HttpResult HttpGet(const std::wstring& host, INTERNET_PORT port,
                   const std::wstring& path, bool secure, int timeout_ms,
                   size_t maximum_bytes) {
    InternetHandle session(WinHttpOpen(L"PuenteCausal/1.0", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                                       WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0));
    if (!session.value) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo iniciar HTTP")));
    }
    WinHttpSetTimeouts(session.value, timeout_ms, timeout_ms, timeout_ms, timeout_ms);
    InternetHandle connection(WinHttpConnect(session.value, host.c_str(), port, 0));
    if (!connection.value) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo conectar con " + host)));
    }
    DWORD flags = secure ? WINHTTP_FLAG_SECURE : 0;
    InternetHandle request(WinHttpOpenRequest(connection.value, L"GET", path.c_str(), nullptr,
                                               WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, flags));
    if (!request.value) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo preparar la descarga")));
    }
    if (!WinHttpSendRequest(request.value, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse(request.value, nullptr)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"Falló la conexión HTTPS o HTTP")));
    }
    DWORD status = 0;
    DWORD status_size = sizeof(status);
    if (!WinHttpQueryHeaders(request.value,
                             WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &status, &status_size,
                             WINHTTP_NO_HEADER_INDEX)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"La respuesta no tiene estado HTTP")));
    }
    std::string body;
    for (;;) {
        DWORD available = 0;
        if (!WinHttpQueryDataAvailable(request.value, &available)) {
            throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"Falló la lectura de la respuesta")));
        }
        if (!available) {
            break;
        }
        if (body.size() + available > maximum_bytes) {
            throw std::runtime_error(WideToUtf8(L"La descarga excedió el tamaño permitido."));
        }
        size_t previous = body.size();
        body.resize(previous + available);
        DWORD received = 0;
        if (!WinHttpReadData(request.value, body.data() + previous, available, &received)) {
            throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"Se interrumpió la descarga")));
        }
        body.resize(previous + received);
        if (!received) {
            break;
        }
    }
    if (status != 200) {
        throw std::runtime_error(WideToUtf8(
            L"El servidor devolvió HTTP " + std::to_wstring(status) + L" para " + path));
    }
    return {status, std::move(body)};
}

std::wstring UrlAfterHost(const std::wstring& url) {
    const size_t scheme = url.find(L"://");
    const size_t slash = url.find(L'/', scheme == std::wstring::npos ? 0 : scheme + 3);
    return slash == std::wstring::npos ? L"/" : url.substr(slash);
}

void DownloadFile(const std::wstring& url, const fs::path& destination) {
    URL_COMPONENTSW parts{sizeof(parts)};
    wchar_t host[256]{};
    parts.lpszHostName = host;
    parts.dwHostNameLength = static_cast<DWORD>(std::size(host));
    if (!WinHttpCrackUrl(url.c_str(), 0, 0, &parts)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"URL de descarga inválida")));
    }
    const std::wstring hostname(parts.lpszHostName, parts.dwHostNameLength);
    const std::wstring path = UrlAfterHost(url);
    AppendLog(L"Descargando " + url);
    HttpResult response = HttpGet(hostname, parts.nPort, path,
                                  parts.nScheme == INTERNET_SCHEME_HTTPS, 30000,
                                  256ULL * 1024ULL * 1024ULL);
    EnsureDirectory(destination.parent_path());
    fs::path partial = destination;
    partial += L".partial";
    {
        std::ofstream output(partial, std::ios::binary | std::ios::trunc);
        if (!output) {
            throw std::runtime_error(WideToUtf8(L"No se pudo abrir para escribir " + partial.wstring()));
        }
        output.write(response.body.data(), static_cast<std::streamsize>(response.body.size()));
        output.close();
        if (!output) {
            throw std::runtime_error(WideToUtf8(L"No se pudo guardar completa la descarga " + partial.wstring()));
        }
    }
    std::error_code error;
    fs::remove(destination, error);
    error.clear();
    fs::rename(partial, destination, error);
    if (error) {
        fs::remove(partial);
        throw std::runtime_error(WideToUtf8(
            L"No se pudo finalizar " + destination.wstring() + L": " + Utf8ToWide(error.message())));
    }
    AppendLog(L"Descarga guardada (" + std::to_wstring(response.body.size()) + L" bytes).");
}

void CheckNt(NTSTATUS status, const wchar_t* action) {
    if (status < 0) {
        std::wostringstream message;
        message << action << L" (NTSTATUS 0x" << std::hex << std::setw(8)
                << std::setfill(L'0') << static_cast<unsigned long>(status) << L")";
        throw std::runtime_error(WideToUtf8(message.str()));
    }
}

std::wstring Sha256File(const fs::path& path) {
    BcryptAlgorithm algorithm;
    CheckNt(BCryptOpenAlgorithmProvider(&algorithm.value, BCRYPT_SHA256_ALGORITHM,
                                        nullptr, 0), L"No se pudo iniciar SHA-256");
    DWORD object_size = 0;
    DWORD digest_size = 0;
    DWORD copied = 0;
    CheckNt(BCryptGetProperty(algorithm.value, BCRYPT_OBJECT_LENGTH,
                              reinterpret_cast<PUCHAR>(&object_size), sizeof(object_size),
                              &copied, 0), L"No se pudo configurar SHA-256");
    CheckNt(BCryptGetProperty(algorithm.value, BCRYPT_HASH_LENGTH,
                              reinterpret_cast<PUCHAR>(&digest_size), sizeof(digest_size),
                              &copied, 0), L"No se pudo configurar SHA-256");
    std::vector<unsigned char> object(object_size);
    std::vector<unsigned char> digest(digest_size);
    BcryptHash hash;
    CheckNt(BCryptCreateHash(algorithm.value, &hash.value, object.data(), object_size,
                             nullptr, 0, 0), L"No se pudo crear SHA-256");
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error(WideToUtf8(L"No se pudo abrir para verificar " + path.wstring()));
    }
    char buffer[65536];
    while (input) {
        input.read(buffer, sizeof(buffer));
        std::streamsize amount = input.gcount();
        if (amount > 0) {
            CheckNt(BCryptHashData(hash.value, reinterpret_cast<PUCHAR>(buffer),
                                   static_cast<ULONG>(amount), 0),
                    L"No se pudo calcular SHA-256");
        }
    }
    if (!input.eof()) {
        throw std::runtime_error(WideToUtf8(L"Falló la lectura para verificar " + path.wstring()));
    }
    CheckNt(BCryptFinishHash(hash.value, digest.data(), digest_size, 0),
            L"No se pudo terminar SHA-256");
    std::wostringstream output;
    output << std::hex << std::setfill(L'0');
    for (unsigned char byte : digest) {
        output << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return output.str();
}

std::wstring PowerShellPath() {
    wchar_t windows_directory[MAX_PATH]{};
    UINT count = GetWindowsDirectoryW(windows_directory, MAX_PATH);
    if (!count || count >= MAX_PATH) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se encontró la carpeta de Windows")));
    }
    return (fs::path(windows_directory) /
            L"System32\\WindowsPowerShell\\v1.0\\powershell.exe").wstring();
}

void ExpandArchive(const fs::path& archive, const fs::path& destination) {
    EnsureDirectory(destination);
    RunProcess({PowerShellPath(), L"-NoLogo", L"-NoProfile", L"-NonInteractive",
                L"-ExecutionPolicy", L"Bypass", L"-Command",
                L"Expand-Archive -LiteralPath $args[0] -DestinationPath $args[1] -Force",
                archive.wstring(), destination.wstring()}, InstallRoot());
}

void RemoveOwnedDirectory(const fs::path& directory) {
    fs::path root = fs::absolute(InstallRoot()).lexically_normal();
    fs::path candidate = fs::absolute(directory).lexically_normal();
    auto root_iterator = root.begin();
    auto candidate_iterator = candidate.begin();
    for (; root_iterator != root.end(); ++root_iterator, ++candidate_iterator) {
        if (candidate_iterator == candidate.end() ||
            root_iterator->wstring() != candidate_iterator->wstring()) {
            throw std::runtime_error("Se bloqueó una eliminación fuera de la carpeta del lanzador.");
        }
    }
    if (candidate == root) {
        throw std::runtime_error("Se bloqueó la eliminación de toda la carpeta del lanzador.");
    }
    std::error_code error;
    fs::remove_all(candidate, error);
    if (error) {
        throw std::runtime_error(WideToUtf8(
            L"No se pudo limpiar " + candidate.wstring() + L": " + Utf8ToWide(error.message())));
    }
}

fs::path FindDirectoryWithFile(const fs::path& root, const std::wstring& marker) {
    if (fs::is_regular_file(root / marker)) {
        return root;
    }
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_directory() && fs::is_regular_file(entry.path() / marker)) {
            return entry.path();
        }
    }
    throw std::runtime_error(WideToUtf8(L"El archivo descargado no contiene " + marker));
}

bool SourceIsComplete() {
    fs::path app = AppRoot();
    return fs::is_regular_file(app / L"requirements.txt") &&
           fs::is_regular_file(app / L"servicio.py") &&
           fs::is_regular_file(app / L"servicio_core.py") &&
           fs::is_regular_file(app / L"artifacts" / L"alias_champion.json") &&
           fs::is_regular_file(app / L"artifacts" / L"registro" / kChampion / L"manifest.json");
}

std::wstring Stamp() {
    SYSTEMTIME now{};
    GetLocalTime(&now);
    wchar_t text[64]{};
    swprintf_s(text, L"%04u%02u%02u-%02u%02u%02u-%lu", now.wYear, now.wMonth,
               now.wDay, now.wHour, now.wMinute, now.wSecond, GetCurrentProcessId());
    return text;
}

void MoveAside(const fs::path& source, const std::wstring& label) {
    fs::path backup_root = InstallRoot() / L"respaldo";
    EnsureDirectory(backup_root);
    fs::path destination = backup_root / (label + L"-" + Stamp());
    fs::rename(source, destination);
    AppendLog(L"La instalación anterior se conservó en " + destination.wstring());
}

void EnsureSource() {
    if (SourceIsComplete()) {
        AppendLog(L"El código fuente y el champion v0008 ya están presentes; se reutilizan.");
        return;
    }
    fs::path root = InstallRoot();
    fs::path archive = root / L"descargas" / L"prototipo-v1.0.1.zip";
    fs::path extracted = root / L"trabajo" / L"fuente";
    RemoveOwnedDirectory(extracted);
    DownloadFile(kProjectUrl, archive);
    AppendLog(L"Descomprimiendo el código del repositorio.");
    ExpandArchive(archive, extracted);
    fs::path source = FindDirectoryWithFile(extracted, L"requirements.txt");
    if (!fs::is_regular_file(source / L"servicio.py")) {
        throw std::runtime_error(WideToUtf8(L"El paquete descargado no contiene servicio.py."));
    }
    if (fs::exists(AppRoot())) {
        MoveAside(AppRoot(), L"app-incompleta");
    }
    EnsureDirectory(AppRoot().parent_path());
    fs::rename(source, AppRoot());
    RemoveOwnedDirectory(extracted);
    if (!SourceIsComplete()) {
        throw std::runtime_error(WideToUtf8(
            L"El paquete instalado está incompleto o no incluye el champion v0008."));
    }
    AppendLog(L"Código instalado en " + AppRoot().wstring());
}

bool IsArm64() {
    USHORT process_machine = IMAGE_FILE_MACHINE_UNKNOWN;
    USHORT native_machine = IMAGE_FILE_MACHINE_UNKNOWN;
    using Function = BOOL(WINAPI*)(HANDLE, USHORT*, USHORT*);
    HMODULE kernel = GetModuleHandleW(L"kernel32.dll");
    auto function = kernel ? reinterpret_cast<Function>(
        GetProcAddress(kernel, "IsWow64Process2")) : nullptr;
    return function && function(GetCurrentProcess(), &process_machine, &native_machine) &&
           native_machine == IMAGE_FILE_MACHINE_ARM64;
}

void EnsureUv() {
    if (fs::is_regular_file(UvExecutable())) {
        AppendLog(L"uv ya está disponible localmente; se reutiliza.");
        return;
    }
    const bool arm64 = IsArm64();
    const std::wstring url = arm64 ? kUvArm64Url : kUvX64Url;
    const std::wstring expected = arm64 ? kUvArm64Sha256 : kUvX64Sha256;
    fs::path archive = InstallRoot() / L"descargas" /
        (std::wstring(L"uv-") + kUvVersion + (arm64 ? L"-arm64.zip" : L"-x64.zip"));
    DownloadFile(url, archive);
    std::wstring actual = Sha256File(archive);
    if (actual != expected) {
        fs::remove(archive);
        throw std::runtime_error(WideToUtf8(
            L"SHA-256 de uv no coincide. El archivo se eliminó y no se ejecutó."));
    }
    AppendLog(L"SHA-256 de uv verificado: " + actual);
    fs::path extracted = InstallRoot() / L"trabajo" / L"uv";
    RemoveOwnedDirectory(extracted);
    ExpandArchive(archive, extracted);
    fs::path uv_directory = FindDirectoryWithFile(extracted, L"uv.exe");
    fs::path target = UvExecutable().parent_path();
    EnsureDirectory(target);
    fs::copy_file(uv_directory / L"uv.exe", UvExecutable(), fs::copy_options::overwrite_existing);
    RemoveOwnedDirectory(extracted);
    RunProcess({UvExecutable().wstring(), L"--version"}, InstallRoot());
}

void RunChecked(const std::vector<std::wstring>& arguments) {
    RunProcess(arguments, AppRoot());
}

void InstallApplication(bool repair) {
    CheckWriteAccess();
    if (repair && fs::exists(AppRoot() / L".venv")) {
        fs::path venv = AppRoot() / L".venv";
        MoveAside(venv, L"entorno");
        AppendLog(L"Se creará un entorno nuevo; el anterior se conservó como respaldo.");
    } else if (fs::exists(AppRoot() / L".venv") && !fs::is_regular_file(VenvPython())) {
        MoveAside(AppRoot() / L".venv", L"entorno-incompleto");
    }
    EnsureSource();
    EnsureUv();
    ConfigureToolEnvironment();
    if (!fs::is_regular_file(VenvPython())) {
        AppendLog(L"Creando .venv con Python 3.13 administrado por uv.");
        RunChecked({UvExecutable().wstring(), L"venv", L"--python", L"3.13",
                    L"--managed-python", (AppRoot() / L".venv").wstring()});
    } else {
        AppendLog(L"El entorno virtual ya existe; no se recrea ni se vacía.");
    }
    RunChecked({VenvPython().wstring(), L"--version"});
    AppendLog(L"Instalando o verificando requirements.txt.");
    RunChecked({UvExecutable().wstring(), L"pip", L"install", L"--python",
                VenvPython().wstring(), L"-r", (AppRoot() / L"requirements.txt").wstring()});
    RunChecked({UvExecutable().wstring(), L"pip", L"check", L"--python", VenvPython().wstring()});
    if (!SourceIsComplete()) {
        throw std::runtime_error(WideToUtf8(L"La comprobación final del champion no fue satisfactoria."));
    }
    AppendLog(L"Instalación verificada. No se ejecutó make demo ni make evidencia.");
}

Health ParseHealth(const std::string& body) {
    Health result;
    result.ours = body.find("\"version\"") != std::string::npos &&
                  body.find("\"integridad_valida\"") != std::string::npos;
    if (!result.ours) {
        return result;
    }
    result.integrity = body.find("\"integridad_valida\": true") != std::string::npos ||
                       body.find("\"integridad_valida\":true") != std::string::npos;
    auto string_value = [&](const std::string& key) -> std::string {
        std::string marker = "\"" + key + "\"";
        size_t position = body.find(marker);
        if (position == std::string::npos) {
            return {};
        }
        position = body.find(':', position + marker.size());
        if (position == std::string::npos) {
            return {};
        }
        position = body.find('"', position + 1);
        if (position == std::string::npos) {
            return {};
        }
        size_t end = body.find('"', position + 1);
        return end == std::string::npos ? std::string{} : body.substr(position + 1, end - position - 1);
    };
    result.version = string_value("version");
    result.gate = string_value("estado_puerta");
    return result;
}

Health CheckHealth(int timeout_ms = 800) {
    try {
        HttpResult response = HttpGet(L"127.0.0.1", 8000, L"/salud", false,
                                      timeout_ms, 1024 * 1024);
        return ParseHealth(response.body);
    } catch (const std::exception&) {
        return {};
    }
}

bool OwnedServiceRunning() {
    std::lock_guard lock(g_service_mutex);
    return g_service.process && WaitForSingleObject(g_service.process, 0) == WAIT_TIMEOUT;
}

void CloseOwnedServiceHandles() {
    if (g_service.process) {
        CloseHandle(g_service.process);
    }
    if (g_service.job) {
        CloseHandle(g_service.job);
    }
    g_service = {};
}

void StopOwnedService() {
    std::lock_guard lock(g_service_mutex);
    if (!g_service.process) {
        return;
    }
    AppendLog(L"Deteniendo el servicio y sus procesos hijos.");
    if (g_service.job) {
        TerminateJobObject(g_service.job, 0);
    } else {
        TerminateProcess(g_service.process, 0);
    }
    WaitForSingleObject(g_service.process, 5000);
    CloseOwnedServiceHandles();
}

void LaunchService() {
    HANDLE raw_job = CreateJobObjectW(nullptr, nullptr);
    if (!raw_job) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo preparar el control del servicio")));
    }
    Handle job(raw_job);
    JOBOBJECT_EXTENDED_LIMIT_INFORMATION limits{};
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
    if (!SetInformationJobObject(job.value, JobObjectExtendedLimitInformation,
                                 &limits, sizeof(limits))) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo configurar el control del servicio")));
    }
    EnsureDirectory(ServiceLogPath().parent_path());
    SECURITY_ATTRIBUTES security{sizeof(security), nullptr, TRUE};
    Handle log(CreateFileW(ServiceLogPath().c_str(), GENERIC_WRITE, FILE_SHARE_READ,
                           &security, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr));
    if (log.value == INVALID_HANDLE_VALUE) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo abrir el registro del servicio")));
    }
    SetFilePointer(log.value, 0, nullptr, FILE_END);
    STARTUPINFOW startup{sizeof(startup)};
    startup.dwFlags = STARTF_USESHOWWINDOW | STARTF_USESTDHANDLES;
    startup.wShowWindow = SW_HIDE;
    startup.hStdInput = GetStdHandle(STD_INPUT_HANDLE);
    startup.hStdOutput = log.value;
    startup.hStdError = log.value;
    std::vector<std::wstring> arguments{
        VenvPython().wstring(), L"-m", L"uvicorn", L"servicio:app",
        L"--host", L"127.0.0.1", L"--port", L"8000"};
    std::wstring command = CommandLine(arguments);
    std::vector<wchar_t> buffer(command.begin(), command.end());
    buffer.push_back(L'\0');
    ConfigureToolEnvironment();
    CheckEnvironment(L"SIC_ESCENARIO", L"synthetic/ihdp");
    CheckEnvironment(L"SIC_VERSION_ESPERADA", kChampion);
    PROCESS_INFORMATION information{};
    AppendLog(L"Iniciando Uvicorn con synthetic/ihdp, sin activar PowerShell.");
    if (!CreateProcessW(arguments.front().c_str(), buffer.data(), nullptr, nullptr, TRUE,
                        CREATE_NO_WINDOW | CREATE_SUSPENDED, nullptr, AppRoot().c_str(),
                        &startup, &information)) {
        throw std::runtime_error(WideToUtf8(WindowsError(GetLastError(), L"No se pudo iniciar Uvicorn")));
    }
    Handle process(information.hProcess);
    Handle thread(information.hThread);
    if (!AssignProcessToJobObject(job.value, process.value)) {
        DWORD code = GetLastError();
        TerminateProcess(process.value, 1);
        throw std::runtime_error(WideToUtf8(WindowsError(code, L"No se pudo asociar Uvicorn al control de procesos")));
    }
    if (ResumeThread(thread.value) == static_cast<DWORD>(-1)) {
        DWORD code = GetLastError();
        TerminateJobObject(job.value, 1);
        throw std::runtime_error(WideToUtf8(WindowsError(code, L"No se pudo reanudar Uvicorn")));
    }
    {
        std::lock_guard lock(g_service_mutex);
        g_service.process = process.release();
        g_service.job = job.release();
        g_service.pid = information.dwProcessId;
    }
}

void AssertInstalled() {
    if (!SourceIsComplete() || !fs::is_regular_file(VenvPython())) {
        throw std::runtime_error(WideToUtf8(
            L"La instalación no está completa. Pulsa «Instalar / verificar» primero."));
    }
}

Completion InstallWorkflow(bool repair) {
    StopOwnedService();
    InstallApplication(repair);
    return {repair ? Operation::repair : Operation::install, true, false,
            L"Instalación lista. Pulsa «Iniciar servicio» y luego «Abrir ATE»."};
}

Completion StartWorkflow() {
    Health existing = CheckHealth();
    if (existing.ours) {
        return {Operation::start, true, true,
                L"El servicio ya estaba activo: " + Utf8ToWide(existing.version) +
                L" · puerta " + Utf8ToWide(existing.gate)};
    }
    if (OwnedServiceRunning()) {
        throw std::runtime_error(WideToUtf8(
            L"El proceso iniciado por el lanzador sigue vivo, pero /salud no responde. "
            L"Pulsa «Detener», revisa servicio.log y vuelve a intentarlo."));
    }
    AssertInstalled();
    LaunchService();
    const auto deadline = std::chrono::steady_clock::now() + 60s;
    Health health;
    do {
        {
            std::lock_guard lock(g_service_mutex);
            if (g_service.process && WaitForSingleObject(g_service.process, 0) == WAIT_OBJECT_0) {
                DWORD code = 0;
                GetExitCodeProcess(g_service.process, &code);
                CloseOwnedServiceHandles();
                throw std::runtime_error(WideToUtf8(
                    L"Uvicorn terminó con código " + std::to_wstring(code) +
                    L". Abre el registro para ver servicio.log."));
            }
        }
        health = CheckHealth(500);
        if (health.ours) {
            std::wstring message = L"Servicio activo en http://127.0.0.1:8000 · " +
                Utf8ToWide(health.version) + L" · puerta " + Utf8ToWide(health.gate);
            AppendLog(message + L". Abre /efecto para el ATE y /docs para la API.");
            return {Operation::start, true, true, message};
        }
        std::this_thread::sleep_for(500ms);
    } while (std::chrono::steady_clock::now() < deadline);
    StopOwnedService();
    throw std::runtime_error(WideToUtf8(
        L"El servicio no respondió en /salud durante 60 segundos y fue detenido. "
        L"Revisa servicio.log; no se cambió la puerta ni la abstención."));
}

Completion StopWorkflow() {
    bool owned = false;
    {
        std::lock_guard lock(g_service_mutex);
        owned = g_service.process != nullptr;
    }
    StopOwnedService();
    Health health = CheckHealth();
    if (health.ours) {
        return {Operation::stop, true, true,
                owned ? L"El proceso del lanzador se detuvo, pero otro servicio del prototipo sigue en el puerto 8000."
                      : L"Hay un servicio activo no iniciado por este lanzador; no se detuvo un proceso ajeno."};
    }
    return {Operation::stop, true, false,
            owned ? L"Servicio detenido correctamente."
                  : L"No había un servicio iniciado por este lanzador."};
}

Completion RefreshWorkflow() {
    Health health = CheckHealth(500);
    if (health.ours) {
        return {Operation::refresh, true, true,
                L"Servicio activo · " + Utf8ToWide(health.version) + L" · puerta " +
                Utf8ToWide(health.gate) + L" · integridad " +
                (health.integrity ? L"válida" : L"NO válida")};
    }
    if (SourceIsComplete() && fs::is_regular_file(VenvPython())) {
        return {Operation::refresh, true, false,
                L"Instalación encontrada. Pulsa «Iniciar servicio»."};
    }
    return {Operation::refresh, true, false,
            L"Pulsa «Instalar / verificar». No hace falta abrir una terminal."};
}

void SetStatus(const std::wstring& text) {
    if (g_status) {
        SetWindowTextW(g_status, text.c_str());
    }
}

void UpdateButtons() {
    EnableWindow(g_install_button, !g_busy);
    EnableWindow(g_start_button, !g_busy);
    EnableWindow(g_stop_button, !g_busy);
    EnableWindow(g_repair_button, !g_busy);
    SendMessageW(g_progress, PBM_SETMARQUEE, g_busy ? TRUE : FALSE, 0);
    ShowWindow(g_progress, g_busy ? SW_SHOW : SW_HIDE);
}

void StartWorker(Operation operation, const std::function<Completion()>& work) {
    if (g_busy) {
        return;
    }
    g_busy = true;
    UpdateButtons();
    SetStatus(L"Trabajando… la ventana seguirá respondiendo.");
    g_worker = std::thread([operation, work]() {
        auto completion = std::make_unique<Completion>();
        completion->operation = operation;
        try {
            Completion result = work();
            *completion = std::move(result);
        } catch (const std::exception& error) {
            completion->ok = false;
            completion->message = Utf8ToWide(error.what());
        } catch (...) {
            completion->ok = false;
            completion->message = L"Error desconocido. Revisa lanzador.log.";
        }
        completion->running = OwnedServiceRunning() || CheckHealth().ours;
        AppendLog((completion->ok ? L"OK: " : L"ERROR: ") + completion->message);
        if (!PostMessageW(g_window, kMessageDone, 0,
                          reinterpret_cast<LPARAM>(completion.release()))) {
            AppendLog(L"No se pudo notificar el resultado a la ventana.");
        }
    });
}

HFONT MakeFont(int size, int weight, const wchar_t* name) {
    return CreateFontW(size, 0, 0, 0, weight, FALSE, FALSE, FALSE, DEFAULT_CHARSET,
                       OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS, CLEARTYPE_QUALITY,
                       DEFAULT_PITCH | FF_DONTCARE, name);
}

HWND MakeControl(const wchar_t* class_name, const wchar_t* text, DWORD style,
                 int x, int y, int width, int height, int identifier = 0) {
    HWND control = CreateWindowExW(
        std::wcscmp(class_name, L"EDIT") == 0 ? WS_EX_CLIENTEDGE : 0,
        class_name, text, style,
        x, y, width, height, g_window,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(identifier)),
        GetModuleHandleW(nullptr), nullptr);
    if (control && g_text_font) {
        SendMessageW(control, WM_SETFONT, reinterpret_cast<WPARAM>(g_text_font), TRUE);
    }
    return control;
}

void BuildInterface(HWND window) {
    g_window = window;
    g_text_font = MakeFont(-16, FW_NORMAL, L"Segoe UI");
    g_title_font = MakeFont(-26, FW_SEMIBOLD, L"Segoe UI");
    g_mono_font = MakeFont(-14, FW_NORMAL, L"Consolas");
    HWND title = MakeControl(L"STATIC", L"Puente Causal · instalación local",
                             WS_CHILD | WS_VISIBLE, 24, 18, 790, 36);
    SendMessageW(title, WM_SETFONT, reinterpret_cast<WPARAM>(g_title_font), TRUE);
    MakeControl(L"STATIC",
                L"Windows sin terminal: 1) instala, 2) inicia, 3) abre el ATE. "
                L"Datos sintéticos; champion v0008; escenario synthetic/ihdp.",
                WS_CHILD | WS_VISIBLE, 26, 60, 790, 38);
    g_path = MakeControl(L"EDIT", InstallRoot().wstring().c_str(),
                         WS_CHILD | WS_VISIBLE | ES_READONLY | ES_AUTOHSCROLL,
                         26, 105, 788, 26);
    g_install_button = MakeControl(L"BUTTON", L"1. Instalar / verificar",
                                   WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
                                   26, 147, 250, 36, kInstall);
    g_start_button = MakeControl(L"BUTTON", L"2. Iniciar servicio",
                                 WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_DEFPUSHBUTTON,
                                 290, 147, 250, 36, kStart);
    g_stop_button = MakeControl(L"BUTTON", L"Detener",
                                WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
                                554, 147, 120, 36, kStop);
    g_repair_button = MakeControl(L"BUTTON", L"Reparar entorno",
                                  WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
                                  688, 147, 126, 36, kRepair);
    g_progress = MakeControl(PROGRESS_CLASSW, L"",
                             WS_CHILD | PBS_MARQUEE | PBS_SMOOTH,
                             26, 190, 788, 8);
    SendMessageW(g_progress, PBM_SETMARQUEE, FALSE, 40);
    g_status = MakeControl(L"STATIC", L"Comprobando el estado local…",
                           WS_CHILD | WS_VISIBLE | SS_LEFTNOWORDWRAP,
                           26, 208, 788, 42);
    g_log_view = MakeControl(L"EDIT", L"",
                             WS_CHILD | WS_VISIBLE | WS_VSCROLL | ES_MULTILINE |
                                 ES_AUTOVSCROLL | ES_READONLY,
                             26, 258, 788, 245);
    SendMessageW(g_log_view, WM_SETFONT, reinterpret_cast<WPARAM>(g_mono_font), TRUE);
    MakeControl(L"BUTTON", L"3. Abrir ATE",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
                26, 522, 150, 38, kOpenEffect);
    MakeControl(L"BUTTON", L"Abrir /docs",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
                188, 522, 150, 38, kOpenDocs);
    MakeControl(L"BUTTON", L"Abrir registros",
                WS_CHILD | WS_VISIBLE | WS_TABSTOP | BS_PUSHBUTTON,
                350, 522, 160, 38, kOpenLog);
    MakeControl(L"STATIC",
                L"El servicio es local, no producción pública. Cerrar esta ventana detiene el servicio que haya iniciado. "
                L"Los archivos de registro no se envían a Internet.",
                WS_CHILD | WS_VISIBLE, 524, 519, 290, 54);
}

void OpenUrl(const wchar_t* suffix) {
    std::wstring url = std::wstring(kBaseUrl) + suffix;
    INT_PTR result = reinterpret_cast<INT_PTR>(
        ShellExecuteW(g_window, L"open", url.c_str(), nullptr, nullptr, SW_SHOWNORMAL));
    if (result <= 32) {
        MessageBoxW(g_window, L"No se pudo abrir el navegador. Copia la dirección del estado o del registro.",
                    L"Puente Causal", MB_ICONWARNING | MB_OK);
    }
}

void OpenLogFolder() {
    try {
        EnsureDirectory(LogPath().parent_path());
        INT_PTR result = reinterpret_cast<INT_PTR>(ShellExecuteW(
            g_window, L"open", LogPath().parent_path().c_str(), nullptr, nullptr, SW_SHOWNORMAL));
        if (result <= 32) {
            throw std::runtime_error(WideToUtf8(L"Windows no pudo abrir la carpeta de registros."));
        }
    } catch (const std::exception& error) {
        MessageBoxW(g_window, Utf8ToWide(error.what()).c_str(), L"Puente Causal",
                    MB_ICONERROR | MB_OK);
    }
}

LRESULT CALLBACK WindowProcedure(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    switch (message) {
    case WM_CREATE:
        try {
            BuildInterface(window);
            StartWorker(Operation::refresh, RefreshWorkflow);
            return 0;
        } catch (const std::exception& error) {
            MessageBoxW(window, Utf8ToWide(error.what()).c_str(),
                        L"Puente Causal · no se pudo iniciar", MB_ICONERROR | MB_OK);
            return -1;
        }
    case WM_CTLCOLORSTATIC: {
        HDC device = reinterpret_cast<HDC>(wparam);
        SetBkMode(device, TRANSPARENT);
        return reinterpret_cast<LRESULT>(GetSysColorBrush(COLOR_WINDOW));
    }
    case kMessageLog: {
        std::unique_ptr<std::wstring> line(reinterpret_cast<std::wstring*>(lparam));
        std::wstring text = *line;
        std::replace(text.begin(), text.end(), L'\r', L' ');
        size_t position = 0;
        while ((position = text.find(L'\n', position)) != std::wstring::npos) {
            text.replace(position, 1, L"\r\n");
            position += 2;
        }
        if (text.size() < 2 || text.compare(text.size() - 2, 2, L"\r\n") != 0) {
            text += L"\r\n";
        }
        int length = GetWindowTextLengthW(g_log_view);
        SendMessageW(g_log_view, EM_SETSEL, length, length);
        SendMessageW(g_log_view, EM_REPLACESEL, FALSE,
                     reinterpret_cast<LPARAM>(text.c_str()));
        SendMessageW(g_log_view, EM_SCROLLCARET, 0, 0);
        return 0;
    }
    case kMessageDone: {
        std::unique_ptr<Completion> completion(reinterpret_cast<Completion*>(lparam));
        if (g_worker.joinable()) {
            g_worker.join();
        }
        g_busy = false;
        UpdateButtons();
        SetStatus(completion->message);
        if (!completion->ok && completion->operation != Operation::refresh) {
            std::wstring detail = completion->message +
                L"\n\nRegistro: " + LogPath().wstring() +
                L"\nSi Windows impidió escribir, revisa permisos, antivirus o Control de acceso a carpetas.";
            MessageBoxW(window, detail.c_str(), L"Puente Causal · no se completó la operación",
                        MB_ICONERROR | MB_OK);
        }
        return 0;
    }
    case WM_COMMAND:
        switch (LOWORD(wparam)) {
        case kInstall:
            StartWorker(Operation::install, [] { return InstallWorkflow(false); });
            return 0;
        case kRepair:
            if (MessageBoxW(window,
                            L"Se conservará el entorno anterior en una carpeta de respaldo y se creará uno nuevo. "
                            L"No se regenerarán estimaciones, artefactos ni el champion. ¿Continuar?",
                            L"Reparar entorno", MB_YESNO | MB_ICONQUESTION) == IDYES) {
                StartWorker(Operation::repair, [] { return InstallWorkflow(true); });
            }
            return 0;
        case kStart:
            StartWorker(Operation::start, StartWorkflow);
            return 0;
        case kStop:
            StartWorker(Operation::stop, StopWorkflow);
            return 0;
        case kOpenEffect:
            OpenUrl(L"/efecto");
            return 0;
        case kOpenDocs:
            OpenUrl(L"/docs");
            return 0;
        case kOpenLog:
            OpenLogFolder();
            return 0;
        default:
            break;
        }
        break;
    case WM_CLOSE:
        if (g_busy) {
            MessageBoxW(window, L"Espera a que termine la operación en curso. El registro muestra el progreso.",
                        L"Puente Causal", MB_ICONINFORMATION | MB_OK);
            return 0;
        }
        if (!OwnedServiceRunning() ||
            MessageBoxW(window,
                        L"Al cerrar se detendrá el servicio iniciado por este lanzador. ¿Salir?",
                        L"Puente Causal", MB_YESNO | MB_ICONQUESTION) == IDYES) {
            StopOwnedService();
            DestroyWindow(window);
        }
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcW(window, message, wparam, lparam);
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

int SmokeTest() {
    try {
        InstallApplication(false);
        if (CheckHealth().ours) {
            AppendLog(L"La prueba integral exige un puerto 8000 libre antes de arrancar.");
            return 31;
        }
        Completion started = StartWorkflow();
        if (!started.ok || !OwnedServiceRunning()) {
            StopOwnedService();
            return 32;
        }
        Health health = CheckHealth(3000);
        if (!health.ours || !health.integrity || health.version != "v0008" ||
            health.gate != "pasa") {
            StopOwnedService();
            return 33;
        }
        HttpResult effect = HttpGet(L"127.0.0.1", 8000, L"/efecto", false, 5000,
                                    1024 * 1024);
        if (effect.body.find("\"efecto\"") == std::string::npos ||
            effect.body.find("\"ic95\"") == std::string::npos ||
            (effect.body.find("\"integridad_valida\": true") == std::string::npos &&
             effect.body.find("\"integridad_valida\":true") == std::string::npos)) {
            StopOwnedService();
            return 34;
        }
        StopOwnedService();
        AppendLog(L"PRUEBA INTEGRAL: instalación, champion, puerta, /salud y /efecto correctos.");
        return 0;
    } catch (const std::exception& error) {
        AppendLog(L"ERROR en la prueba integral: " + Utf8ToWide(error.what()));
        StopOwnedService();
        return 30;
    }
}

int SelfTest() {
    if (QuoteArgument(L"") != L"\"\"" || QuoteArgument(L"simple") != L"simple" ||
        QuoteArgument(L"con espacio") != L"\"con espacio\"") {
        return 10;
    }
    const std::vector<std::wstring> arguments{
        L"", L"simple", L"C:\\ruta con espacios\\archivo.txt",
        L"comilla:\"", L"barra-final\\"};
    for (const auto& argument : arguments) {
        std::wstring command = L"sonda " + QuoteArgument(argument);
        int count = 0;
        LPWSTR* parsed = CommandLineToArgvW(command.c_str(), &count);
        bool matches = parsed && count == 2 && argument == parsed[1];
        if (parsed) {
            LocalFree(parsed);
        }
        if (!matches) {
            return 14;
        }
    }
    Health health = ParseHealth(
        R"({"estado":"ok","version":"v0008","integridad_valida": true,"estado_puerta":"pasa"})");
    if (!health.ours || !health.integrity || health.version != "v0008" || health.gate != "pasa") {
        return 11;
    }
    if (ParseHealth("not json").ours) {
        return 12;
    }
    fs::path temporary = fs::temp_directory_path() /
        (L"puente-causal-sha256-" + std::to_wstring(GetCurrentProcessId()) + L".txt");
    {
        std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
        output << "abc";
    }
    const std::wstring digest = Sha256File(temporary);
    std::error_code error;
    fs::remove(temporary, error);
    if (digest != L"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") {
        return 13;
    }
    return 0;
}

}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int show_command) {
    int argument_count = 0;
    LPWSTR* arguments = CommandLineToArgvW(GetCommandLineW(), &argument_count);
    bool self_test = false;
    bool smoke_test = false;
    for (int index = 1; index < argument_count; ++index) {
        if (std::wstring(arguments[index]) == L"--self-test") {
            self_test = true;
        } else if (std::wstring(arguments[index]) == L"--smoke-test") {
            smoke_test = true;
        }
    }
    if (arguments) {
        LocalFree(arguments);
    }
    if (self_test) {
        try {
            return SelfTest();
        } catch (...) {
            return 20;
        }
    }
    try {
        fs::path log = LogPath();
        EnsureDirectory(log.parent_path());
        g_log_file.open(log, std::ios::app);
    } catch (const std::exception&) {
        // La ventana seguirá mostrando errores aunque tampoco pueda abrir el registro.
    }
    if (smoke_test) {
        return SmokeTest();
    }
    INITCOMMONCONTROLSEX controls{sizeof(controls), ICC_STANDARD_CLASSES | ICC_PROGRESS_CLASS};
    InitCommonControlsEx(&controls);
    WNDCLASSEXW window_class{sizeof(window_class)};
    window_class.hInstance = instance;
    window_class.lpszClassName = kWindowClass;
    window_class.lpfnWndProc = WindowProcedure;
    window_class.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    window_class.hbrBackground = GetSysColorBrush(COLOR_WINDOW);
    window_class.hIcon = LoadIconW(nullptr, IDI_APPLICATION);
    window_class.hIconSm = LoadIconW(nullptr, IDI_APPLICATION);
    if (!RegisterClassExW(&window_class)) {
        MessageBoxW(nullptr, L"No se pudo registrar la ventana del lanzador.",
                    L"Puente Causal", MB_ICONERROR | MB_OK);
        return 1;
    }
    HWND window = CreateWindowExW(0, kWindowClass, L"Puente Causal · Windows sin terminal",
                                  WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                                  CW_USEDEFAULT, CW_USEDEFAULT, 852, 628, nullptr, nullptr,
                                  instance, nullptr);
    if (!window) {
        MessageBoxW(nullptr, L"No se pudo crear la ventana del lanzador.",
                    L"Puente Causal", MB_ICONERROR | MB_OK);
        return 2;
    }
    ShowWindow(window, show_command);
    UpdateWindow(window);
    MSG message{};
    while (GetMessageW(&message, nullptr, 0, 0) > 0) {
        if (!IsDialogMessageW(window, &message)) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }
    if (g_log_file.is_open()) {
        g_log_file.close();
    }
    if (g_text_font) DeleteObject(g_text_font);
    if (g_title_font) DeleteObject(g_title_font);
    if (g_mono_font) DeleteObject(g_mono_font);
    return static_cast<int>(message.wParam);
}
