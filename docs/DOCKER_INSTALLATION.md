# Docker Installation Guide for Brain MVP

## 🐳 **Installing Docker on macOS**

### **Method 1: Docker Desktop (Recommended)**

1. **Download Docker Desktop**
   - Visit: https://docs.docker.com/desktop/install/mac-install/
   - Download Docker Desktop for Mac (Intel or Apple Silicon)

2. **Install Docker Desktop**
   - Open the downloaded `.dmg` file
   - Drag Docker to Applications folder
   - Launch Docker Desktop from Applications

3. **Start Docker Desktop**
   - Docker Desktop will start automatically
   - Wait for the Docker icon in the menu bar to show "Docker Desktop is running"

4. **Verify Installation**
   ```bash
   docker --version
   docker-compose --version
   ```

### **Method 2: Homebrew (Alternative)**

```bash
# Install Docker
brew install --cask docker

# Start Docker Desktop
open /Applications/Docker.app
```

### **Method 3: Command Line Only (Advanced)**

```bash
# Install Docker Engine and Compose
brew install docker docker-compose

# Note: You'll need to set up Docker daemon separately
```

## 🧪 **Testing Docker Installation**

Once Docker is installed, test the Brain MVP setup:

```bash
# Run the comprehensive test script
./scripts/test-docker-setup.sh
```

## 🚀 **Quick Start After Installation**

1. **Start Development Environment**
   ```bash
   ./scripts/docker-dev.sh start
   ```

2. **Access Services**
   - Application: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database: localhost:5432
   - Redis: localhost:6379

3. **Stop Services**
   ```bash
   ./scripts/docker-dev.sh stop
   ```

## 🔧 **System Requirements**

- **Memory**: 4GB+ RAM available for Docker
- **Disk Space**: 10GB+ free space
- **macOS**: 10.15+ (Catalina or later)
- **Architecture**: Intel x64 or Apple Silicon

## 🐛 **Troubleshooting**

### **Docker Desktop Won't Start**
- Check system requirements
- Restart your Mac
- Try reinstalling Docker Desktop

### **Permission Issues**
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER

# Restart terminal or log out/in
```

### **Port Conflicts**
If ports 8000, 5432, or 6379 are in use:
```bash
# Check what's using the ports
lsof -i :8000
lsof -i :5432
lsof -i :6379

# Stop conflicting services or modify docker-compose.yml
```

### **Memory Issues**
- Increase Docker Desktop memory allocation
- Close other applications
- Consider using production compose with resource limits

## 📚 **Additional Resources**

- [Docker Desktop Documentation](https://docs.docker.com/desktop/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🆘 **Getting Help**

If you encounter issues:

1. Check Docker Desktop is running
2. Run the test script: `./scripts/test-docker-setup.sh`
3. Check logs: `docker-compose logs`
4. Review system resources
5. Consult the troubleshooting section above

---

**Next**: Once Docker is installed, return to [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for full deployment instructions.