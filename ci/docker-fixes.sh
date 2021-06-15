curl http://pkgconfig.freedesktop.org/releases/pkg-config-0.29.2.tar.gz -L -o pkg-config.tar.gz && \
    mkdir pkg-config && \
    tar -zxf pkg-config.tar.gz -C pkg-config --strip-components 1 && \
    cd pkg-config && \
    ./configure --prefix=/usr/local --with-internal-glib --disable-host-tool && \
    make && \
    make install 
    
curl ftp://ftp.gnu.org/gnu/m4/m4-latest.tar.gz -L -o m4.tar.gz && \
    mkdir m4 && \
    tar -zxf m4.tar.gz -C m4 --strip-components 1 && \
    cd m4 && \
    ./configure --prefix=/usr/local && \
    make && \
    make install 

curl -L http://install.perlbrew.pl | bash && \
    . ~/perl5/perlbrew/etc/bashrc && \
    echo '. /root/perl5/perlbrew/etc/bashrc' >> /etc/bashrc && \
    perlbrew install perl-5.29.0 -j 4 -n && \
    perlbrew switch perl-5.29.0 

curl http://ftp.gnu.org/gnu/automake/automake-1.16.1.tar.gz -L -o automake.tar.gz && \
    mkdir automake && \
    tar -zxf automake.tar.gz -C automake --strip-components 1 && \
    cd automake && \
    ./configure --prefix=/usr/local && \
    make && \
    make install

curl http://ftp.gnu.org/gnu/autoconf/autoconf-latest.tar.gz -L -o autoconf.tar.gz && \
    mkdir autoconf && \
    tar -zxf autoconf.tar.gz -C autoconf --strip-components 1 && \
    cd autoconf && \
    ./configure --prefix=/usr/local && \
    make && \
    make install

curl http://ftp.gnu.org/gnu/libtool/libtool-2.4.6.tar.gz -L -o libtool.tar.gz && \
    mkdir libtool && \
    tar -zxf libtool.tar.gz -C libtool --strip-components 1 && \
    cd libtool && \
    ./configure --prefix=/usr/local && \
    make && \
    make install

# bison
curl https://ftp.gnu.org/gnu/bison/bison-3.7.6.tar.xz -L -o bison.tar.xz && \
    mkdir bison && \
    xz --decompress --stdout bison.tar.xz | tar xf - -C bison --strip-components 1 && \
    cd bison && \
    ./configure --prefix=/usr/local && \
    make && \
    make install

# flex
curl https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz -L -o  flex.tar.gz && \
    mkdir flex && \
    tar -zxf flex.tar.gz -C flex --strip-components 1 && \
    cd flex && \
    ./configure --prefix=/usr/local && \
    make && \
    make install
