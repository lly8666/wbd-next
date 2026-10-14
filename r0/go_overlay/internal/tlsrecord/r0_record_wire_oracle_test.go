package tlsrecord

import (
	_ "embed"
	"bytes"
	"encoding/hex"
	"fmt"
	"strconv"
	"strings"
	"testing"
)

//go:embed r0_record_wire_v1.txt
var r0PinnedGoWireOracle string

type r0WireVector struct {
	name string
	pn uint64
	kind byte
	padding int
	payload []byte
	wire []byte
}
func r0VectorRows(t *testing.T) []r0WireVector {
	t.Helper()
	var rows []r0WireVector
	for _, line := range strings.Split(r0PinnedGoWireOracle, "\n") {
		if line=="" || strings.HasPrefix(line, "#") {continue}
		parts:=strings.Split(line,"|")
		if len(parts)!=6 {t.Fatalf("bad fixture field count: %q",line)}
		pn,err:=strconv.ParseUint(parts[1],10,64)
		if err!=nil {t.Fatal(err)}
		kind,err:=strconv.ParseUint(parts[2],10,8)
		if err!=nil {t.Fatal(err)}
		padding,err:=strconv.Atoi(parts[3])
		if err!=nil {t.Fatal(err)}
		payload,err:=hex.DecodeString(parts[4])
		if err!=nil {t.Fatal(err)}
		wire,err:=hex.DecodeString(parts[5])
		if err!=nil {t.Fatal(err)}
		rows=append(rows,r0WireVector{parts[0],pn,byte(kind),padding,payload,wire})
	}
	if len(rows)!=6 {t.Fatalf("expected six pinned vectors, got %d",len(rows))}
	return rows
}

func TestR0RecordRealPinnedGoSealAndOpenSixFixtures(t *testing.T) {
	keys:=testKeys(t)
	sealer,err:=NewSealer(keys,MaxWireLen)
	if err!=nil {t.Fatal(err)}
	opener,err:=NewOpener(keys,MaxWireLen)
	if err!=nil {t.Fatal(err)}
	for _,v:=range r0VectorRows(t){
		t.Run(v.name,func(t *testing.T){
			actual,err:=sealRecord(keys,sealer.aead,sealer.maxBody,v.pn,v.kind,v.payload,v.padding)
			if err!=nil {t.Fatalf("real Go seal: %v",err)}
			if !bytes.Equal(actual,v.wire) {
				t.Fatalf("Go sealed bytes differ from locked independent wire golden: %x",actual)
			}
			if len(actual)<FixedWireOverhead ||
			   int(actual[3])<<8|int(actual[4])!=len(actual)-OuterHeaderLen {
				t.Fatal("legacy Go header/body length inconsistent")
			}
			rec,err:=opener.OpenRecord(v.wire)
			if err!=nil {t.Fatalf("real Go authenticated opener: %v",err)}
			if rec.PN!=v.pn || rec.Kind!=v.kind || !bytes.Equal(rec.Payload,v.payload) {
				t.Fatalf("real Go opened wrong PN/kind/payload: got pn=%d kind=%d bytes=%x",rec.PN,rec.Kind,rec.Payload)
			}
			if v.padding==9 && !strings.Contains(v.name,"padded") {t.Fatal("unexpected padded vector name")}
		})
	}
}
func TestR0RecordRealGoLengthFailClosedWithoutMagicScan(t *testing.T){
	rows:=r0VectorRows(t)
	keys:=testKeys(t)
	decoder,err:=NewDecoder(keys,MaxWireLen)
	if err!=nil {t.Fatal(err)}
	bad:=[]byte{0x17,0x03,0x03,0x00,0x01,0x00}
	combined:=append(append([]byte{},bad...),rows[1].wire...)
	got:=decoder.OpenPayload(combined)
	if len(got)!=1 || got[0].Err!=ErrInvalidLength {
		t.Fatalf("decoder improperly scanned after bogus length: %+v",got)
	}
	if decoder.Stats().Delivered!=0 {t.Fatal("invalid length delivered a business frame")}
	if got:=fmt.Sprintf("%x",rows[0].wire[:5]);got!="170303001a" {t.Fatalf("old Go minimum head changed: %s",got)}
}
